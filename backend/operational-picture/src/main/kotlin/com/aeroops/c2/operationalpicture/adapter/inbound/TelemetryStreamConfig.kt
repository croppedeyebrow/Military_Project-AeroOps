package com.aeroops.c2.operationalpicture.adapter.inbound

import com.aeroops.c2.operationalpicture.application.RecordObservation
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty
import org.springframework.boot.context.properties.bind.ConstructorBinding
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.data.redis.connection.RedisConnectionFactory
import org.springframework.data.redis.connection.stream.MapRecord
import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.data.redis.stream.StreamMessageListenerContainer
import tools.jackson.databind.ObjectMapper
import java.time.Clock

/**
 * 텔레메트리 스트림 구독을 조립한다.
 *
 * 왜 조건부인가(`aeroops.telemetry.stream.enabled`): 이 구독은 Redis를 요구한다. DB만 띄우는 시험
 * (마이그레이션·저장소 시험 등)에서 Redis까지 강제하면 느려지고, 그 시험들의 관심사와도 멀다. 그래서
 * 기본은 켜 두되(운영에서 필요), 시험 소스의 공통 설정에서 꺼 두고 스트림 시험만 명시적으로 켠다
 * (`bootstrap/src/test/resources/application.properties`).
 *
 * 패키지 위치(2026-11-01 이동): 처음에는 bootstrap(루트 패키지)에 두었는데, 그러면 루트 모듈이
 * `adapter.inbound`라는 **모듈 내부 패키지**의 타입을 직접 참조하게 되어 Modulith 검증이 실패했다
 * (2-2에서 세운 "다른 모듈의 내부에 접근하지 않는다" 규칙이 실제로 잡아낸 사례다). 모듈이 자기 인프라
 * 조립을 소유하는 것이 올바른 구조라, 설정을 이 모듈 안으로 옮겼다. bootstrap은 컴포넌트 스캔으로 발견만 한다.
 *
 * 연관 코드: 소비 로직은 [TelemetryStreamConsumer], 유스케이스는 [RecordObservation],
 * Redis 접속 설정은 `application.yml`의 `spring.data.redis`.
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(
    name = ["aeroops.telemetry.stream.enabled"],
    havingValue = "true",
    matchIfMissing = true,
)
class TelemetryStreamConfig {

    /**
     * 스트림·그룹 이름 등을 설정에서 읽는다.
     *
     * `@ConstructorBinding`을 쓰지 않고 수동으로 만드는 이유: [TelemetryStreamProperties]는 Spring에
     * 의존하지 않는 평범한 data class다(operational-picture 모듈은 라이브러리라 Boot 설정 바인딩을 끌어오지
     * 않는다). 조립 지점인 여기서 설정값을 읽어 넘긴다.
     */
    @Bean
    fun telemetryStreamProperties(
        @org.springframework.beans.factory.annotation.Value("\${aeroops.telemetry.stream.key:aeroops:telemetry:raw}")
        streamKey: String,
        @org.springframework.beans.factory.annotation.Value("\${aeroops.telemetry.stream.group:telemetry-shadow-kotlin}")
        group: String,
        @org.springframework.beans.factory.annotation.Value("\${aeroops.telemetry.stream.consumer:c2-core-1}")
        consumer: String,
    ) = TelemetryStreamProperties(streamKey = streamKey, consumerGroup = group, consumerName = consumer)

    @Bean
    fun telemetryStreamConsumer(
        recordObservation: RecordObservation,
        redis: StringRedisTemplate,
        objectMapper: ObjectMapper,
        properties: TelemetryStreamProperties,
        clock: Clock,
    ) = TelemetryStreamConsumer(recordObservation, redis, objectMapper, properties, clock)

    /**
     * 메시지를 받아 [TelemetryStreamConsumer]에 넘기는 컨테이너.
     *
     * 왜 직접 루프를 돌지 않나: legacy는 직접 `while` 루프를 돌렸고, 예외 한 번에 루프가 끝나 수집이 영구히
     * 멈춘 적이 있다(D-2). Spring Data의 컨테이너는 구독 생명주기·재시도·스레드를 관리하므로 그 실수를
     * 구조적으로 피한다.
     *
     * `autoAcknowledge(false)`: ACK 시점을 우리가 정한다. 처리에 성공했을 때만 ACK해야 실패한 메시지가
     * pending으로 남아 재처리될 수 있다([TelemetryStreamConsumer.onMessage] 설명).
     */
    @Bean(initMethod = "start", destroyMethod = "stop")
    fun telemetryStreamContainer(
        connectionFactory: RedisConnectionFactory,
        consumer: TelemetryStreamConsumer,
        properties: TelemetryStreamProperties,
    ): StreamMessageListenerContainer<String, MapRecord<String, String, String>> {
        consumer.ensureConsumerGroup()

        val options = StreamMessageListenerContainer
            .StreamMessageListenerContainerOptions.builder()
            .pollTimeout(properties.pollTimeout)
            .build()

        val container = StreamMessageListenerContainer.create(connectionFactory, options)
        container.receive(consumer.consumer(), consumer.streamOffset(), consumer::onMessage)
        return container
    }
}
