package com.aeroops.c2.operationalpicture.domain

import com.aeroops.c2.shared.AssetId
import com.aeroops.c2.shared.BootId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotEquals

/**
 * `ObservationKey`의 중복 판정 규칙 시험.
 * 근거 문서: ADR 0005, 추적표 REQ-TEL-02(중복은 한 번만 저장)·REQ-TEL-05(재부팅해도 새 프레임을 버리지 않음).
 */
class ObservationKeyTest {
    private val asset = AssetId("drone-01")
    private val bootA = BootId("boot-a")
    private val bootB = BootId("boot-b")

    @Test
    fun `세 값이 모두 같으면 같은 관측이다(중복)`() {
        assertEquals(ObservationKey(asset, bootA, 7), ObservationKey(asset, bootA, 7))
    }

    @Test
    fun `재부팅하면 같은 sequence_no라도 다른 관측이다`() {
        // legacy 결함의 재현: (drone-01, 0)이 부팅 A와 B에서 모두 존재한다. 예전 키로는 두 번째가 중복으로
        // 버려졌지만, bootId가 키에 있으니 서로 다른 관측이다.
        assertNotEquals(ObservationKey(asset, bootA, 0), ObservationKey(asset, bootB, 0))
    }

    @Test
    fun `기체가 다르면 같은 부팅·번호라도 다른 관측이다`() {
        assertNotEquals(
            ObservationKey(AssetId("drone-01"), bootA, 1),
            ObservationKey(AssetId("drone-02"), bootA, 1),
        )
    }

    @Test
    fun `sequence_no는 0 이상이어야 한다`() {
        ObservationKey(asset, bootA, 0)
        assertFailsWith<IllegalArgumentException> { ObservationKey(asset, bootA, -1) }
    }
}
