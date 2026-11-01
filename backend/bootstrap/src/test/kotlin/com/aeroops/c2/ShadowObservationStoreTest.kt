package com.aeroops.c2

import com.aeroops.c2.operationalpicture.adapter.inbound.TelemetryWireFrame
import com.aeroops.c2.operationalpicture.adapter.inbound.toObservation
import com.aeroops.c2.operationalpicture.application.ObservationStore
import com.aeroops.c2.operationalpicture.domain.Quality
import com.aeroops.c2.shared.AssetId
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.jdbc.core.JdbcTemplate
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
 * Shadow 저장소가 **legacy와 같은 판정**을 내는지 실제 PostgreSQL에서 확인한다.
 *
 * 왜 실제 DB인가: 핵심 규칙이 전부 SQL의 `ON CONFLICT`와 `where ... event_time <`에 있다. 가짜 저장소로는
 * 그 규칙을 검증할 수 없고, 정작 중요한 동시성·제약 동작도 확인되지 않는다.
 *
 * 확인하는 불변조건(docs/planning/13 §4):
 * - 같은 관측은 한 번만 저장된다(멱등) — 1번
 * - 늦게 도착한 과거 관측이 최신 상태를 덮어쓰지 않는다 — 1번, 3단계 완료 게이트
 * - 재부팅으로 sequence_no가 0부터 다시 시작해도 새 관측으로 인식된다 — ADR 0005
 *
 * 연관 코드: [ObservationStore], `JdbcObservationStore`, 스키마는 `V3__operational_picture_shadow.sql`,
 * legacy 대응은 `telemetry/repository.py`의 `process_frame`.
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest
class ShadowObservationStoreTest(
    @Autowired private val store: ObservationStore,
    @Autowired private val jdbc: JdbcTemplate,
) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.empty()
    }

    private val baseTime: Instant = Instant.parse("2026-01-01T00:00:00Z")

    /** 시험마다 다른 기체 id를 써서 서로 간섭하지 않게 한다(같은 컨테이너를 공유하므로). */
    private fun newAssetId() = "drone-${UUID.randomUUID().toString().take(8)}"

    private fun frame(
        assetId: String,
        seconds: Long,
        sequenceNo: Long,
        bootId: String? = null,
        altitude: Double = 50.0,
    ) = TelemetryWireFrame(
        assetId = assetId,
        eventTime = baseTime.plusSeconds(seconds),
        sequenceNo = sequenceNo,
        bootId = bootId,
        latitude = 37.3947,
        longitude = 127.1112,
        altitudeM = altitude,
        batteryPct = 90.0,
    ).toObservation(baseTime.plusSeconds(seconds))

    private fun observationCount(assetId: String): Int = jdbc.queryForObject(
        "select count(*) from shadow.observation where asset_id = ?", Int::class.java, assetId,
    )!!

    // --- 멱등(중복 판정) ----------------------------------------------------------------------

    @Test
    fun `같은 관측을 두 번 저장해도 한 건만 남는다`() {
        val assetId = newAssetId()
        val observation = frame(assetId, 0, 0)

        val first = store.record(observation)
        val second = store.record(observation)

        assertTrue(first.isNew, "첫 저장은 신규여야 한다")
        assertTrue(!second.isNew, "두 번째는 중복으로 판정돼야 한다")
        assertEquals(1, observationCount(assetId))
    }

    @Test
    fun `중복이면 최신 상태를 건드리지 않는다`() {
        // legacy의 `latest_updated = ... if is_new else False`와 같은 동작이어야 한다.
        val assetId = newAssetId()
        store.record(frame(assetId, 0, 0))

        val duplicate = store.record(frame(assetId, 0, 0))

        assertTrue(!duplicate.isNew)
        assertTrue(!duplicate.latestUpdated, "중복인데 최신 상태가 갱신되면 안 된다")
    }

    @Test
    fun `재부팅으로 sequence_no가 겹쳐도 새 관측으로 저장된다`() {
        // ADR 0005의 핵심: boot_id가 키에 없으면 이 프레임이 "중복"으로 버려진다(legacy의 결함).
        val assetId = newAssetId()
        store.record(frame(assetId, 0, 0, bootId = "boot-a"))

        val afterReboot = store.record(frame(assetId, 10, 0, bootId = "boot-b"))

        assertTrue(afterReboot.isNew, "부팅이 다르면 같은 sequence_no라도 새 관측이다")
        assertEquals(2, observationCount(assetId))
    }

    // --- 최신 상태 후퇴 방지(완료 게이트) --------------------------------------------------------

    @Test
    fun `더 최신 관측은 최신 상태를 갱신한다`() {
        val assetId = newAssetId()
        store.record(frame(assetId, 0, 0, altitude = 50.0))

        val result = store.record(frame(assetId, 10, 1, altitude = 100.0))

        assertTrue(result.latestUpdated)
        assertEquals(100.0, store.findSnapshot(AssetId(assetId))?.position?.value?.altitudeM)
    }

    @Test
    fun `늦게 도착한 과거 관측은 저장되지만 최신 상태를 덮어쓰지 않는다`() {
        // 이력(원본)은 보존해야 하고, 최신 상태는 후퇴하면 안 된다 — 둘을 구분하는 것이 핵심이다.
        val assetId = newAssetId()
        store.record(frame(assetId, 10, 10, altitude = 100.0))

        val late = store.record(frame(assetId, 5, 5, altitude = 50.0))

        assertTrue(late.isNew, "과거 관측도 원본으로는 저장돼야 한다(이력·재생용)")
        assertTrue(!late.latestUpdated, "과거 관측이 최신 상태를 덮어쓰면 화면의 기체가 뒤로 점프한다")
        assertEquals(100.0, store.findSnapshot(AssetId(assetId))?.position?.value?.altitudeM)
        assertEquals(2, observationCount(assetId))
    }

    @Test
    fun `같은 event_time이면 최신 상태를 갱신하지 않는다`() {
        // legacy의 부등호가 `<`라서 같은 시각은 갱신하지 않는다. 다르게 구현하면 Golden Replay가 어긋난다.
        val assetId = newAssetId()
        store.record(frame(assetId, 5, 1, altitude = 50.0))

        val sameTime = store.record(frame(assetId, 5, 2, altitude = 999.0))

        assertTrue(sameTime.isNew, "sequence_no가 다르므로 원본은 새로 저장된다")
        assertTrue(!sameTime.latestUpdated)
        assertEquals(50.0, store.findSnapshot(AssetId(assetId))?.position?.value?.altitudeM)
    }

    @Test
    fun `역순으로 도착해도 최종 상태는 가장 최신 관측이다`() {
        val assetId = newAssetId()
        listOf(3L, 1L, 5L, 2L, 4L).forEach { store.record(frame(assetId, it, it, altitude = it * 10.0)) }

        val snapshot = store.findSnapshot(AssetId(assetId))

        assertEquals(baseTime.plusSeconds(5), snapshot?.eventTime)
        assertEquals(50.0, snapshot?.position?.value?.altitudeM)
        assertEquals(5, observationCount(assetId), "원본은 모두 보존된다")
    }

    // --- 저장·복원 왕복 -----------------------------------------------------------------------

    @Test
    fun `품질과 관측 시각이 저장 후에도 그대로 복원된다`() {
        val assetId = newAssetId()
        // 자세는 일부만(PARTIAL), RSSI는 없음(UNKNOWN), 배터리는 범위 초과(INVALID)인 프레임
        val wire = TelemetryWireFrame(
            assetId = assetId,
            eventTime = baseTime,
            sequenceNo = 0,
            latitude = 37.0,
            longitude = 127.0,
            altitudeM = 50.0,
            batteryPct = 150.0,
            rollDeg = 10.0,
        )
        store.record(wire.toObservation(baseTime))

        val snapshot = store.findSnapshot(AssetId(assetId))

        assertNotNull(snapshot)
        assertEquals(Quality.KNOWN, snapshot.position.quality)
        assertEquals(Quality.PARTIAL, snapshot.attitude.quality)
        assertEquals(setOf("roll"), snapshot.attitude.reportedFields, "무엇이 왔는지도 보존돼야 한다")
        assertEquals(Quality.INVALID, snapshot.battery.quality)
        assertNull(snapshot.battery.value, "범위를 벗어난 값은 값으로 복원되지 않는다")
        assertEquals(Quality.UNKNOWN, snapshot.link.quality)
        assertEquals(baseTime, snapshot.position.observedAt)
    }

    @Test
    fun `보고받은 적 없는 기체는 최신 상태가 없다`() {
        assertNull(store.findSnapshot(AssetId(newAssetId())), "0이나 빈 값으로 지어내면 안 된다")
    }

    @Test
    fun `전체 조회는 기체별 최신 상태를 돌려준다`() {
        val a = newAssetId()
        val b = newAssetId()
        store.record(frame(a, 0, 0))
        store.record(frame(b, 0, 0))

        val all = store.findAllSnapshots().map { it.assetId.value }

        assertTrue(a in all && b in all)
    }
}
