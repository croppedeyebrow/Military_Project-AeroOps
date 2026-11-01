package com.aeroops.c2.operationalpicture.domain

import com.aeroops.c2.shared.AssetId
import com.aeroops.c2.shared.BootId
import java.time.Duration
import java.time.Instant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * 최신 상태 갱신 규칙 — 3단계 완료 게이트의 핵심인 **"오래된 관측이 최신 상태를 덮어쓰지 않는다"** 를 고정한다.
 *
 * 왜 이 시험이 중요한가: 네트워크는 순서를 보장하지 않는다. 이 규칙이 깨지면 화면의 기체가 뒤로 점프하고,
 * 그 상태로 명령을 내리면 엉뚱한 위치 기준으로 판단하게 된다. Golden Replay의 `out_of_order`·`delay`·
 * `reorder5` 시나리오가 실제로 이 상황을 만든다(docs/planning/13 REQ-TEL-03).
 *
 * 연관 코드: [AssetSnapshot.apply], legacy 대응은 `upsert_latest_state_if_newer`의 `event_time <` 비교.
 */
class AssetSnapshotTest {
    private val asset = AssetId("drone-01")
    private val boot = BootId("boot-a")
    private val t0: Instant = Instant.parse("2026-01-01T00:00:00Z")

    private fun observationAt(seconds: Long, sequenceNo: Long, altitude: Double = 50.0): Observation {
        val eventTime = t0.plusSeconds(seconds)
        return Observation(
            key = ObservationKey(asset, boot, sequenceNo),
            eventTime = eventTime,
            receivedAt = eventTime.plusMillis(100),
            position = ObservedValue.observed(Position(37.0, 127.0, altitude), eventTime, eventTime),
            attitude = ObservedValue.observed(Attitude(0.0, 0.0, 0.0), eventTime, eventTime),
            battery = ObservedValue.observed(BatteryLevel(90.0), eventTime, eventTime),
            link = ObservedValue.observed(LinkQuality(-70.0), eventTime, eventTime),
            flightMode = ObservedValue.observed("AUTO", eventTime, eventTime),
        )
    }

    // --- 후퇴 방지(완료 게이트) ---------------------------------------------------------------

    @Test
    fun `더 최신 관측은 반영된다`() {
        val snapshot = AssetSnapshot.from(observationAt(0, 0))

        val result = snapshot.apply(observationAt(1, 1, altitude = 60.0))

        assertIs<ApplyResult.Applied>(result)
        assertEquals(60.0, result.snapshot.position.value?.altitudeM)
        assertEquals(t0.plusSeconds(1), result.snapshot.eventTime)
    }

    @Test
    fun `늦게 도착한 과거 관측은 최신 상태를 덮어쓰지 않는다`() {
        // 순서가 뒤집힌 상황: 10초 관측이 먼저 반영된 뒤 5초 관측이 도착한다.
        val snapshot = AssetSnapshot.from(observationAt(10, 10, altitude = 100.0))

        val result = snapshot.apply(observationAt(5, 5, altitude = 50.0))

        assertIs<ApplyResult.Ignored>(result)
        assertEquals(IgnoreReason.NOT_NEWER, result.reason)
        // 상태는 그대로여야 한다 — 이것이 깨지면 화면의 기체가 뒤로 점프한다.
        assertEquals(100.0, snapshot.position.value?.altitudeM)
    }

    @Test
    fun `같은 event_time은 갱신하지 않는다(legacy의 부등호와 동일)`() {
        // legacy는 `event_time <` 비교라 같은 시각이면 갱신하지 않는다. 다르게 구현하면 Golden Replay가 어긋난다.
        val snapshot = AssetSnapshot.from(observationAt(5, 5, altitude = 50.0))

        val result = snapshot.apply(observationAt(5, 6, altitude = 999.0))

        assertIs<ApplyResult.Ignored>(result)
        assertEquals(IgnoreReason.NOT_NEWER, result.reason)
    }

    @Test
    fun `다른 기체의 관측은 반영하지 않는다`() {
        val snapshot = AssetSnapshot.from(observationAt(0, 0))
        val other = observationAt(10, 10).let {
            it.copy(key = it.key.copy(assetId = AssetId("drone-02")))
        }

        val result = snapshot.apply(other)

        assertIs<ApplyResult.Ignored>(result)
        assertEquals(IgnoreReason.DIFFERENT_ASSET, result.reason)
    }

    @Test
    fun `역순으로 도착해도 최종 상태는 가장 최신 관측이다`() {
        // Golden Replay의 reorder5 시나리오와 같은 상황을 압축해서 재현한다.
        val arrivalOrder = listOf(3L, 1L, 5L, 2L, 4L)
        var snapshot = AssetSnapshot.from(observationAt(arrivalOrder.first(), arrivalOrder.first()))

        arrivalOrder.drop(1).forEach { seconds ->
            val result = snapshot.apply(observationAt(seconds, seconds))
            if (result is ApplyResult.Applied) snapshot = result.snapshot
        }

        assertEquals(t0.plusSeconds(5), snapshot.eventTime, "가장 최신 관측이 최종 상태여야 한다")
    }

    // --- 조회 시점 품질 재판정 -----------------------------------------------------------------

    @Test
    fun `시간이 흐르면 조회 시점에 STALE로 내려간다`() {
        val snapshot = AssetSnapshot.from(observationAt(0, 0))
        assertEquals(Quality.KNOWN, snapshot.position.quality)

        // 저장 당시엔 KNOWN이었지만 1분이 지난 뒤 조회하면 더 이상 현재 사실이 아니다.
        val refreshed = snapshot.refreshedAt(t0.plus(Duration.ofMinutes(1)))

        assertEquals(Quality.STALE, refreshed.position.quality)
        assertEquals(Quality.STALE, refreshed.battery.quality)
        assertNull(refreshed.position.trustedValue(), "STALE 값은 운용 판단에 쓰이면 안 된다")
    }

    @Test
    fun `기준 시간 안이면 KNOWN을 유지한다`() {
        val snapshot = AssetSnapshot.from(observationAt(0, 0))

        val refreshed = snapshot.refreshedAt(t0.plusSeconds(5)) // 기본 임계 15초 이내

        assertEquals(Quality.KNOWN, refreshed.position.quality)
        assertTrue(refreshed.position.trustedValue() != null)
    }

    @Test
    fun `보고가 없던 값은 시간이 흘러도 UNKNOWN 그대로다`() {
        // UNKNOWN은 "모른다"이지 "오래된 값"이 아니다. STALE로 바꾸면 없던 값이 있었던 것처럼 보인다.
        val base = AssetSnapshot.from(observationAt(0, 0))
        val snapshot = base.copy(battery = ObservedValue.unknown())

        val refreshed = snapshot.refreshedAt(t0.plus(Duration.ofHours(1)))

        assertEquals(Quality.UNKNOWN, refreshed.battery.quality)
    }
}

/** 품질 모델 자체의 규칙. */
class ObservedValueTest {
    private val now: Instant = Instant.parse("2026-01-01T00:00:00Z")

    @Test
    fun `값이 없는데 KNOWN이라고 주장할 수 없다`() {
        // 모델 수준에서 막지 않으면 "값은 없는데 믿어도 된다"는 모순된 상태가 소비자에게 전달된다.
        assertFailsWith<IllegalArgumentException> {
            ObservedValue<Position>(value = null, observedAt = now, quality = Quality.KNOWN)
        }
    }

    @Test
    fun `INVALID는 원본 값을 보존한다`() {
        // 진단을 위해 "무엇이 왔길래 거부했는지"를 남긴다.
        val invalid = ObservedValue.invalid(BatteryLevel(50.0), now)
        assertEquals(50.0, invalid.value?.percent)
        assertNull(invalid.trustedValue(), "INVALID 값은 운용 판단에 쓰이면 안 된다")
    }

    @Test
    fun `KNOWN만 신뢰할 수 있다`() {
        val trustable = Quality.entries.filter { it.isTrustworthy }
        assertEquals(listOf(Quality.KNOWN), trustable)
    }
}

/** 도메인 값 객체의 범위 검증 — legacy 계약과 같은 기준이어야 Golden Replay가 성립한다. */
class DomainValueRangeTest {
    @Test
    fun `위경도와 고도의 범위를 강제한다`() {
        Position(90.0, 180.0, 10_000.0) // 경계값은 허용
        assertFailsWith<IllegalArgumentException> { Position(90.1, 0.0, 0.0) }
        assertFailsWith<IllegalArgumentException> { Position(0.0, 180.1, 0.0) }
        assertFailsWith<IllegalArgumentException> { Position(0.0, 0.0, 10_001.0) }
    }

    @Test
    fun `자세 각도의 범위를 강제한다`() {
        Attitude(-180.0, -90.0, 180.0)
        assertFailsWith<IllegalArgumentException> { Attitude(181.0, 0.0, 0.0) }
        assertFailsWith<IllegalArgumentException> { Attitude(0.0, 91.0, 0.0) } // pitch는 ±90
    }

    @Test
    fun `배터리와 RSSI의 범위를 강제한다`() {
        BatteryLevel(0.0); BatteryLevel(100.0); LinkQuality(-130.0); LinkQuality(0.0)
        assertFailsWith<IllegalArgumentException> { BatteryLevel(100.1) }
        assertFailsWith<IllegalArgumentException> { LinkQuality(0.1) } // RSSI는 0 이하
    }
}
