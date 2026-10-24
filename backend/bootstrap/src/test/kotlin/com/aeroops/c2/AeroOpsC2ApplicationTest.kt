package com.aeroops.c2

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.health.actuate.endpoint.HealthEndpoint
import org.springframework.boot.health.contributor.Status
import org.springframework.boot.test.context.SpringBootTest
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * 앱 컨텍스트가 실제로 기동되고 헬스 엔드포인트가 UP인지 확인한다(2단계 최소 완료 조건).
 * HTTP 계층 시험은 DB·보안을 붙인 뒤 Controller와 함께 추가한다.
 */
@SpringBootTest
class AeroOpsC2ApplicationTest(@Autowired private val health: HealthEndpoint) {
    @Test
    fun `컨텍스트가 기동되고 헬스가 UP이다`() {
        assertEquals(Status.UP, health.health().status)
    }
}
