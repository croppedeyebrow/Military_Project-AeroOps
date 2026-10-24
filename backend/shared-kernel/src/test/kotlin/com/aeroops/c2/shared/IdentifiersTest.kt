package com.aeroops.c2.shared

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class BootIdTest {
    @Test
    fun `UUID 형식의 부팅 ID를 받아들인다`() {
        val uuid = "3f2b8c1e-9a4d-4c55-8e0a-7d1b2c3d4e5f"
        assertEquals(uuid, BootId(uuid).value)
    }

    @Test
    fun `경계 길이 1자와 64자는 허용한다`() {
        BootId("a")
        BootId("a".repeat(64))
    }

    @Test
    fun `빈 값과 65자 이상은 거부한다`() {
        assertFailsWith<IllegalArgumentException> { BootId("") }
        assertFailsWith<IllegalArgumentException> { BootId("a".repeat(65)) }
    }

    @Test
    fun `허용되지 않은 문자는 거부한다`() {
        assertFailsWith<IllegalArgumentException> { BootId("boot id") }
        assertFailsWith<IllegalArgumentException> { BootId("boot:1") }
        assertFailsWith<IllegalArgumentException> { BootId("부팅") }
    }

    @Test
    fun `전환기 LEGACY 값은 유효한 부팅 ID다`() {
        assertEquals("legacy", BootId.LEGACY.value)
    }
}

class AssetIdTest {
    @Test
    fun `일반 기체 ID를 받아들인다`() {
        assertEquals("drone-01", AssetId("drone-01").value)
    }

    @Test
    fun `빈 값과 공백뿐인 값은 거부한다`() {
        assertFailsWith<IllegalArgumentException> { AssetId("") }
        assertFailsWith<IllegalArgumentException> { AssetId("   ") }
    }
}
