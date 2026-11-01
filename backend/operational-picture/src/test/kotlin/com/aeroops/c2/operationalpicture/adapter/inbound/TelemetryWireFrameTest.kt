package com.aeroops.c2.operationalpicture.adapter.inbound

import com.aeroops.c2.operationalpicture.domain.Quality
import com.aeroops.c2.shared.BootId
import java.time.Instant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Wire → 도메인 변환(Anti-Corruption Layer) 규칙을 고정한다.
 *
 * 왜 중요한가: 이 변환이 legacy와 어긋나면 Golden Replay의 최종 상태가 달라진다. 특히 **boot_id 없는 v1
 * 프레임을 LEGACY로 정규화**하는 규칙이 깨지면 멱등 키가 달라져 중복 판정이 전부 틀어진다(ADR 0005).
 *
 * 연관 코드: [toObservation], 도메인 품질 모델은 `domain.Quality`, 계약 원본은
 * `tests/contracts/baseline/openapi.json`의 TelemetryFrame.
 */
class TelemetryWireFrameTest {
    private val eventTime: Instant = Instant.parse("2026-01-01T00:00:00Z")
    private val now: Instant = eventTime.plusSeconds(1)

    /** 계약상 필수 필드만 채운 최소 프레임(선택 필드는 전부 비어 있다). */
    private fun minimalFrame() = TelemetryWireFrame(
        assetId = "drone-01",
        eventTime = eventTime,
        sequenceNo = 7,
        latitude = 37.3947,
        longitude = 127.1112,
        altitudeM = 50.0,
        batteryPct = 90.0,
    )

    // --- 멱등 키(ADR 0005) --------------------------------------------------------------------

    @Test
    fun `boot_id가 없는 v1 프레임은 LEGACY 부팅으로 정규화된다`() {
        // 이 규칙이 legacy의 (asset_id, sequence_no) 판정과 같은 결과를 만든다.
        val observation = minimalFrame().toObservation(now)

        assertEquals(BootId.LEGACY, observation.key.bootId)
        assertEquals("drone-01", observation.key.assetId.value)
        assertEquals(7, observation.key.sequenceNo)
    }

    @Test
    fun `boot_id가 있으면 그대로 쓴다(v2)`() {
        val observation = minimalFrame().copy(bootId = "boot-xyz").toObservation(now)

        assertEquals(BootId("boot-xyz"), observation.key.bootId)
    }

    // --- 선택 필드가 없을 때: 0으로 채우지 않는다 -------------------------------------------------

    @Test
    fun `자세가 전혀 없으면 UNKNOWN이다`() {
        val observation = minimalFrame().toObservation(now)

        assertEquals(Quality.UNKNOWN, observation.attitude.quality)
        assertNull(observation.attitude.value, "없는 자세를 0으로 채우면 기체가 수평인 것처럼 보인다")
    }

    @Test
    fun `자세가 일부만 오면 PARTIAL이고 무엇이 왔는지 남긴다`() {
        val observation = minimalFrame().copy(rollDeg = 10.0).toObservation(now)

        assertEquals(Quality.PARTIAL, observation.attitude.quality)
        assertNull(observation.attitude.value)
        assertEquals(setOf("roll"), observation.attitude.reportedFields, "센서 이상 진단의 단서가 된다")
    }

    @Test
    fun `자세 세 각도가 모두 오면 값이 된다`() {
        val observation = minimalFrame()
            .copy(rollDeg = 10.0, pitchDeg = -5.0, yawDeg = 90.0)
            .toObservation(now)

        assertEquals(Quality.KNOWN, observation.attitude.quality)
        assertEquals(10.0, observation.attitude.value?.rollDeg)
        assertEquals(90.0, observation.attitude.value?.yawDeg)
    }

    @Test
    fun `RSSI와 비행모드가 없으면 UNKNOWN이다`() {
        val observation = minimalFrame().toObservation(now)

        assertEquals(Quality.UNKNOWN, observation.link.quality)
        assertEquals(Quality.UNKNOWN, observation.flightMode.quality)
    }

    // --- 범위를 벗어난 값: 프레임 전체를 버리지 않는다 ---------------------------------------------

    @Test
    fun `배터리가 범위를 벗어나도 위치는 살아남는다`() {
        // 센서 하나가 고장 나도 나머지 관측은 쓸모 있다. 프레임 전체를 버리면 기체를 놓친다.
        val observation = minimalFrame().copy(batteryPct = 150.0).toObservation(now)

        assertEquals(Quality.INVALID, observation.battery.quality)
        assertNull(observation.battery.trustedValue(), "INVALID는 운용 판단에 쓰이면 안 된다")
        assertEquals(Quality.KNOWN, observation.position.quality)
        assertEquals(37.3947, observation.position.value?.latitude)
    }

    @Test
    fun `위치가 범위를 벗어나면 위치만 INVALID가 된다`() {
        val observation = minimalFrame().copy(latitude = 91.0).toObservation(now)

        assertEquals(Quality.INVALID, observation.position.quality)
        assertEquals(Quality.KNOWN, observation.battery.quality)
    }

    // --- 시각 처리 ---------------------------------------------------------------------------

    @Test
    fun `received_at이 없으면 현재 시각으로 채운다`() {
        val observation = minimalFrame().toObservation(now)

        assertEquals(now, observation.receivedAt)
        assertEquals(eventTime, observation.eventTime, "관측 시각은 기체가 보고한 값을 그대로 쓴다")
    }

    @Test
    fun `received_at이 있으면 그대로 보존한다`() {
        // 기체 시계와 서버 시계가 다를 수 있어 둘 다 남긴다(docs/planning/05).
        val serverReceived = eventTime.plusMillis(250)
        val observation = minimalFrame().copy(receivedAt = serverReceived).toObservation(now)

        assertEquals(serverReceived, observation.receivedAt)
    }

    @Test
    fun `관측이 오래됐으면 변환 시점에 STALE로 판정된다`() {
        val observation = minimalFrame().toObservation(eventTime.plusSeconds(60))

        assertEquals(Quality.STALE, observation.position.quality)
        assertTrue(observation.position.value != null, "STALE이어도 값 자체는 남는다")
    }
}
