package com.aeroops.c2

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import java.time.Clock

/**
 * 시각의 출처를 빈으로 제공한다.
 *
 * 왜 빈으로 두나: 코드 곳곳에서 `Instant.now()`를 직접 부르면 그 지점마다 시험이 시계를 고정할 수 없다.
 * 신선도 판정(KNOWN↔STALE)처럼 시간에 따라 답이 달라지는 규칙은 시계를 주입받아야 결정적으로 검증된다.
 *
 * 왜 bootstrap에 두나: 여러 모듈이 공유하는 공용 빈이라 특정 경계 컨텍스트가 소유하기에 맞지 않다.
 * 조립 지점이 제공하고 각 모듈은 주입받는다.
 *
 * 연관 코드: 사용처는 `operationalpicture.adapter.inbound.TelemetryStreamConsumer`,
 * 신선도 규칙은 `operationalpicture.domain.FreshnessPolicy`.
 */
@Configuration(proxyBeanMethods = false)
class ClockConfig {
    @Bean
    fun clock(): Clock = Clock.systemUTC()
}
