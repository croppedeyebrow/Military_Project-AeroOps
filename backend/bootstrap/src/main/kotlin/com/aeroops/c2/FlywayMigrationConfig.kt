package com.aeroops.c2

import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

/**
 * Flyway 마이그레이션 직전에 [LegacySchemaGuard]를 끼워 넣는 설정.
 *
 * 왜 이 방식인가: Spring Boot가 Flyway를 자동으로 실행할 때 사용자 정의 지점을 주는 것이
 * `FlywayMigrationStrategy`다. 기본 전략은 `flyway.migrate()`를 곧바로 부르지만, 우리는 그 앞에 "baseline해도
 * 되는 DB인가" 검사가 필요하다(검사 근거는 [LegacySchemaGuard] 참고). 직접 `Flyway` 빈을 만들어 `@PostConstruct`
 * 에서 부르면 Boot의 설정 바인딩(application.yml의 spring.flyway.*)을 우회하게 되므로 쓰지 않았다.
 *
 * 목적: 마이그레이션 순서를 "검사 → migrate"로 고정한다. 검사에 실패하면 migrate가 실행되지 않으므로
 * DB는 변경되지 않는다.
 *
 * 연관 코드: 설정값은 `application.yml`의 `spring.flyway.*`, 스키마는 `db/migration/V1__*.sql`,
 * 시험은 `FreshDatabaseMigrationTest`(빈 DB)·`LegacyDatabaseMigrationTest`(기존 DB).
 *
 * 패키지 위치: Spring Modulith는 `com.aeroops.c2` 바로 아래 패키지를 업무 모듈로 간주한다. 인프라 설정을
 * `config` 같은 하위 패키지에 두면 모듈로 잘못 탐지되므로(ModularityTest가 잡는다) 루트 패키지에 둔다.
 */
@Configuration(proxyBeanMethods = false)
class FlywayMigrationConfig {

    @Bean
    fun flywayMigrationStrategy(): FlywayMigrationStrategy = FlywayMigrationStrategy { flyway ->
        LegacySchemaGuard(flyway.configuration.dataSource).verifyBaselineAllowed()
        flyway.migrate()
    }
}
