package com.aeroops.c2

import com.aeroops.c2.operationalpicture.application.ObservationStore
import com.aeroops.c2.shared.AssetId
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.test.context.TestPropertySource
import org.testcontainers.containers.GenericContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.time.Instant
import java.util.UUID
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Kotlin이 **legacy가 발행한 그대로의 메시지**를 읽어 Shadow Projection을 만드는지 확인한다.
 *
 * 왜 실제 Redis인가: 핵심이 consumer group 동작(메시지 분배·ACK·pending)이라 가짜로는 검증되지 않는다.
 * 특히 "legacy와 **다른 그룹**이어야 같은 메시지를 양쪽이 각자 전부 받는다"는 전제는 실제 Redis에서만
 * 확인할 수 있다(ADR 0004).
 *
 * 메시지를 legacy와 똑같은 모양으로 넣는 이유: 여기서 Kotlin 편한 형식으로 넣으면, 정작 운영에서 legacy가
 * 넣은 메시지를 못 읽어도 시험은 통과한다. 그래서 `payload` 필드에 snake_case JSON 문자열을 담는
 * legacy 방식(`legacy-backend/app/modules/ingestion/router.py`)을 그대로 쓴다.
 *
 * 연관 코드: [TelemetryStreamConsumer], 조립은 [TelemetryStreamConfig], 저장은 `JdbcObservationStore`.
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest
@TestPropertySource(properties = ["aeroops.telemetry.stream.enabled=true"]) // 공통 설정에서 꺼둔 것을 켠다
class TelemetryStreamConsumerTest(
    @Autowired private val redis: StringRedisTemplate,
    @Autowired private val store: ObservationStore,
) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.empty()

        /**
         * ACL 없는 평범한 Redis를 쓴다.
         *
         * 왜 legacy처럼 ACL 사용자를 만들지 않나: 이 시험의 관심사는 "스트림을 읽어 Projection을 만드는가"다.
         * ACL은 legacy 앱이 기동할 때 등록하는 것이라, 여기서 재현하면 시험이 legacy 기동 순서에 묶인다.
         * 채널 분리(ACL)는 legacy 쪽 시험(`test_redis_acl.py`)이 이미 검증한다.
         */
        @Container
        @ServiceConnection
        @JvmStatic
        val redisContainer: GenericContainer<*> =
            GenericContainer("redis:7-alpine").withExposedPorts(6379)
    }

    private val streamKey = "aeroops:telemetry:raw"

    /** legacy가 Redis에 넣는 모양 그대로: `payload` 필드에 snake_case JSON 문자열. */
    private fun publishAsLegacy(
        assetId: String,
        sequenceNo: Long,
        eventTime: Instant,
        altitudeM: Double = 50.0,
        bootId: String? = null,
    ) {
        val bootField = bootId?.let { """"boot_id":"$it",""" } ?: ""
        val json = """
            {$bootField"schema_version":1,"asset_id":"$assetId","event_time":"$eventTime",
             "sequence_no":$sequenceNo,"latitude":37.3947,"longitude":127.1112,
             "altitude_m":$altitudeM,"battery_pct":90.0,"rssi_dbm":-70.0,"flight_mode":"AUTO",
             "received_at":"$eventTime"}
        """.trimIndent().replace("\n", "")
        redis.opsForStream<String, String>().add(streamKey, mapOf("payload" to json))
    }

    /** 비동기 구독이라 결과가 보일 때까지 짧게 기다린다. */
    private fun awaitSnapshot(assetId: String, timeoutMs: Long = 15_000): Any? {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            store.findSnapshot(AssetId(assetId))?.let { return it }
            Thread.sleep(200)
        }
        return null
    }

    @Test
    fun `legacy가 발행한 프레임을 읽어 최신 상태를 만든다`() {
        val assetId = "stream-${UUID.randomUUID().toString().take(8)}"
        val eventTime = Instant.parse("2026-01-01T00:00:00Z")

        publishAsLegacy(assetId, sequenceNo = 0, eventTime = eventTime, altitudeM = 77.0)

        val snapshot = awaitSnapshot(assetId)
        assertNotNull(snapshot, "스트림에서 읽은 관측이 Projection으로 만들어지지 않았다")
        val stored = store.findSnapshot(AssetId(assetId))!!
        assertEquals(77.0, stored.position.value?.altitudeM)
        assertEquals(eventTime, stored.eventTime)
        // boot_id 없는 v1 프레임은 LEGACY로 정규화된다(ADR 0005).
        assertEquals("legacy", stored.lastKey.bootId.value)
    }

    @Test
    fun `여러 프레임을 처리하면 최신 것이 최종 상태가 된다`() {
        val assetId = "stream-${UUID.randomUUID().toString().take(8)}"
        val base = Instant.parse("2026-01-01T00:00:00Z")

        // 역순으로 발행한다 — 늦게 도착한 과거 관측이 최신 상태를 덮어쓰면 안 된다.
        publishAsLegacy(assetId, 2, base.plusSeconds(20), altitudeM = 200.0)
        publishAsLegacy(assetId, 1, base.plusSeconds(10), altitudeM = 100.0)

        awaitSnapshot(assetId)
        Thread.sleep(1500) // 두 번째 메시지까지 처리될 시간을 준다

        val stored = store.findSnapshot(AssetId(assetId))!!
        assertEquals(200.0, stored.position.value?.altitudeM, "과거 관측이 최신 상태를 덮어썼다")
        assertEquals(base.plusSeconds(20), stored.eventTime)
    }

    @Test
    fun `해석할 수 없는 메시지는 흐름을 막지 않는다`() {
        val assetId = "stream-${UUID.randomUUID().toString().take(8)}"

        // 깨진 메시지를 먼저 넣고, 그 뒤 정상 메시지를 넣는다.
        redis.opsForStream<String, String>().add(streamKey, mapOf("payload" to "{ not json"))
        redis.opsForStream<String, String>().add(streamKey, mapOf("unexpected" to "field"))
        publishAsLegacy(assetId, 0, Instant.parse("2026-01-01T00:00:00Z"))

        assertNotNull(awaitSnapshot(assetId), "깨진 메시지 뒤의 정상 메시지가 처리되지 않았다")
    }

    @Test
    fun `legacy와 다른 consumer group을 쓴다`() {
        // 같은 그룹이면 메시지를 서로 나눠 갖게 되어 양쪽 다 일부만 보게 된다(Shadow 비교의 전제가 깨진다).
        val groups = redis.opsForStream<String, String>().groups(streamKey).map { it.groupName() }

        assertTrue("telemetry-shadow-kotlin" in groups, "Kotlin 그룹이 없다: $groups")
        assertTrue("telemetry-processors" !in groups, "legacy 그룹과 같은 이름을 쓰면 안 된다")
    }

    @Test
    fun `처리한 메시지는 ACK되어 pending에 남지 않는다`() {
        val assetId = "stream-${UUID.randomUUID().toString().take(8)}"
        publishAsLegacy(assetId, 0, Instant.parse("2026-01-01T00:00:00Z"))
        awaitSnapshot(assetId)
        Thread.sleep(1000)

        val pending = redis.opsForStream<String, String>()
            .pending(streamKey, "telemetry-shadow-kotlin")

        // 성공한 메시지를 ACK하지 않으면 pending이 계속 쌓여 재처리 대상이 무한히 늘어난다.
        assertEquals(0L, pending.totalPendingMessages, "처리 성공한 메시지가 pending에 남아 있다")
    }

    @Test
    fun `보고받지 못한 기체는 Projection이 없다`() {
        assertNull(store.findSnapshot(AssetId("never-reported-asset")))
    }
}
