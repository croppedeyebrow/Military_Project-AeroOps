package com.aeroops.c2.operationalpicture.adapter.inbound

import com.aeroops.c2.operationalpicture.application.RecordObservation
import org.slf4j.LoggerFactory
import org.springframework.data.redis.connection.stream.Consumer
import org.springframework.data.redis.connection.stream.MapRecord
import org.springframework.data.redis.connection.stream.ReadOffset
import org.springframework.data.redis.connection.stream.StreamOffset
import org.springframework.data.redis.core.StringRedisTemplate
import tools.jackson.databind.ObjectMapper
import java.time.Clock
import java.time.Duration

/**
 * legacy가 발행한 텔레메트리 스트림을 **별도 consumer group**으로 읽어 Shadow Projection을 만든다.
 *
 * 왜 같은 스트림을 읽나(근거 — ADR 0004의 결정): 3단계의 목표는 "같은 입력을 양쪽이 읽고 결과를 비교"하는
 * 것이다. Kotlin이 자기 수신 경로를 따로 만들면 입력이 달라져 비교 자체가 성립하지 않는다.
 *
 * 왜 group을 분리하나: Redis Stream의 consumer group은 "그룹 안에서 메시지를 나눠 갖는" 구조다. legacy와
 * 같은 그룹을 쓰면 메시지가 둘로 쪼개져 **양쪽 다 일부만** 보게 된다. 그룹을 나누면 같은 메시지를 양쪽이
 * 각자 전부 받는다. 이것이 Shadow 비교의 전제다.
 *
 * 읽기 실패를 어떻게 다루나(legacy의 교훈): legacy는 consumer 루프가 Redis 예외 한 번에 영구히 죽어
 * 텔레메트리 수집이 멈춘 적이 있다(docs/dev_history/new_history/01, D-2). 그래서 여기서는 Spring Data의
 * 컨테이너가 관리하는 구독을 쓰고, 메시지 하나의 처리 실패가 구독 전체를 멈추지 않게 각 메시지를 개별로
 * 감싼다. 처리하지 못한 메시지는 ACK하지 않아 pending으로 남는다(유실 대신 재처리 가능).
 *
 * 연관 코드: 유스케이스는 [RecordObservation], Wire 변환은 [toObservation], 설정·구독 등록은
 * bootstrap의 `TelemetryStreamConfig`, legacy 발행부는 `legacy-backend/app/modules/ingestion/router.py`.
 */
class TelemetryStreamConsumer(
    private val recordObservation: RecordObservation,
    private val redis: StringRedisTemplate,
    private val objectMapper: ObjectMapper,
    private val properties: TelemetryStreamProperties,
    private val clock: Clock,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    /**
     * 메시지 한 건을 처리한다. 성공하면 ACK하고, 실패하면 ACK하지 않는다.
     *
     * ACK를 보류하는 이유: ACK는 "이 메시지를 책임지고 처리했다"는 표시다. DB 순단 같은 일시 실패에서
     * ACK해 버리면 그 관측은 영구히 사라진다(legacy에서 실제로 겪은 유실). pending으로 남겨 두면 나중에
     * 다시 가져올 수 있다.
     *
     * 반대로 **해석 자체가 불가능한 메시지**(깨진 JSON, 계약 위반)는 몇 번을 다시 읽어도 같은 결과다.
     * 이런 메시지는 ACK해서 흐름을 막지 않는다 — 대신 오류 로그로 남겨 추적한다.
     */
    fun onMessage(record: MapRecord<String, String, String>) {
        val payload = record.value[PAYLOAD_FIELD]
        if (payload == null) {
            log.error("payload 필드가 없는 메시지: id={} fields={}", record.id, record.value.keys)
            acknowledge(record)
            return
        }

        val frame = try {
            objectMapper.readValue(payload, TelemetryWireFrame::class.java)
        } catch (e: Exception) {
            // 다시 읽어도 같은 결과이므로 ACK한다(흐름을 막지 않는다).
            log.error("텔레메트리 프레임을 해석할 수 없다: id={} reason={}", record.id, e.message)
            acknowledge(record)
            return
        }

        try {
            val result = recordObservation.handle(frame.toObservation(clock.instant()))
            acknowledge(record)
            if (!result.isNew) {
                log.debug("중복 관측: asset={} seq={}", frame.assetId, frame.sequenceNo)
            }
        } catch (e: Exception) {
            // 일시 실패(DB 순단 등)로 본다 — ACK하지 않아 pending에 남고 재처리할 수 있다.
            log.warn(
                "관측 처리 실패(재처리 대상): id={} asset={} seq={} reason={}",
                record.id, frame.assetId, frame.sequenceNo, e.message,
            )
        }
    }

    private fun acknowledge(record: MapRecord<String, String, String>) {
        redis.opsForStream<String, String>().acknowledge(properties.consumerGroup, record)
    }

    /**
     * consumer group이 없으면 만든다(이미 있으면 그대로 둔다).
     *
     * `MKSTREAM`으로 스트림까지 함께 만드는 이유: Kotlin이 legacy보다 먼저 뜰 수 있는데, 그때는 스트림이
     * 아직 없다. 없으면 그룹 생성이 실패해 구독을 시작하지 못한다.
     *
     * 시작 지점을 `$`(지금 이후)가 아니라 `0`으로 두는 이유: Shadow는 "legacy와 같은 입력"을 봐야 하므로
     * 스트림에 이미 쌓인 것부터 읽는다. 다만 Redis에 보존된 범위까지만 볼 수 있다(그보다 과거는 재생으로 메운다).
     */
    fun ensureConsumerGroup() {
        try {
            redis.opsForStream<String, String>()
                .createGroup(properties.streamKey, ReadOffset.from("0"), properties.consumerGroup)
            log.info("consumer group 생성: {} on {}", properties.consumerGroup, properties.streamKey)
        } catch (e: Exception) {
            // 이미 있으면(BUSYGROUP) 정상이다. 그 밖의 오류는 구독 시작 시 다시 드러난다.
            log.debug("consumer group이 이미 있거나 생성에 실패했다: {}", e.message)
        }
    }

    /** 이 소비자가 구독할 위치(그룹의 아직 전달되지 않은 메시지부터). */
    fun streamOffset(): StreamOffset<String> =
        StreamOffset.create(properties.streamKey, ReadOffset.lastConsumed())

    /** 그룹 안에서 이 인스턴스를 식별하는 이름. 여러 인스턴스로 늘릴 때 서로 다른 이름이어야 한다. */
    fun consumer(): Consumer = Consumer.from(properties.consumerGroup, properties.consumerName)

    private companion object {
        /** legacy가 payload를 담는 필드 이름(`xadd ... payload <json>`). */
        const val PAYLOAD_FIELD = "payload"
    }
}

/**
 * 스트림 소비 설정.
 *
 * 기본값이 legacy와 같은 스트림·다른 그룹인 이유는 위 클래스 설명 참고. 환경변수로 덮어쓸 수 있게 둔 것은
 * 시험·다중 인스턴스에서 이름을 바꿔야 하기 때문이다.
 *
 * 연관: legacy 설정은 `legacy-backend/app/core/config.py`(telemetry_stream_name, telemetry_consumer_group).
 */
data class TelemetryStreamProperties(
    /** legacy와 **같은** 스트림. 같은 입력을 봐야 비교가 성립한다. */
    val streamKey: String = "aeroops:telemetry:raw",
    /** legacy(`telemetry-processors`)와 **다른** 그룹. 같으면 메시지를 서로 나눠 갖게 된다. */
    val consumerGroup: String = "telemetry-shadow-kotlin",
    val consumerName: String = "c2-core-1",
    /** 메시지가 없을 때 블로킹하는 시간. 너무 짧으면 빈 폴링이 잦고, 길면 종료가 늦어진다. */
    val pollTimeout: Duration = Duration.ofSeconds(2),
)
