/*
 * 실행·조립 모듈 — Spring Boot 앱의 진입점과 설정만 둔다. 업무 규칙은 두지 않는다(각 경계 컨텍스트 모듈이 소유).
 *
 * 왜 모든 컨텍스트 모듈에 의존하나: 이 모듈이 "조립 지점"이라서다. 그리고 Modulith의 모듈 탐색과 ArchUnit
 *   분석은 클래스패스에 올라온 클래스만 볼 수 있으므로, 6개 모듈이 여기 있어야 ModularityTest·
 *   LayeringRulesTest가 전부를 검사한다. (반대로 컨텍스트 모듈끼리의 의존은 각 모듈 build 파일과
 *   allowedDependencies가 제한한다 — bootstrap만 예외적으로 전부를 안다.)
 * 연관: 검증 시험은 src/test/.../ModularityTest.kt, LayeringRulesTest.kt, 위반 샘플은 src/test/.../archfixture.
 */
plugins {
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.kotlin.spring) // @Component 등 Spring 어노테이션 클래스를 자동으로 open 처리
}

val archunitVersion = libs.versions.archunit.get()

dependencies {
    implementation(project(":shared-kernel"))
    implementation(project(":mission"))
    implementation(project(":operational-picture"))
    implementation(project(":safety-policy"))
    implementation(project(":audit"))
    implementation(project(":command-control"))
    implementation(project(":incident"))

    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    // Spring Boot 4는 Jackson 3(패키지 tools.jackson)을 쓴다 — Kotlin data class 직렬화에 필요
    implementation("tools.jackson.module:jackson-module-kotlin")
    // 모듈 구조를 런타임/시험에서 읽는 Modulith 코어(ApplicationModules 등)
    implementation("org.springframework.modulith:spring-modulith-starter-core")
    // 이벤트 발행 기록(Transactional Outbox) — 업무 트랜잭션과 같은 커밋으로 event_publication에 남기고,
    // 전달은 그 뒤 비동기로 한다(V2 마이그레이션, EventPublicationOutboxTest 참고).
    implementation("org.springframework.modulith:spring-modulith-starter-jpa")

    // --- 영속성 (Unit 2-3) -------------------------------------------------------------
    // JPA: Aggregate 단위 저장(planning/02 "Spring 기술 선택"). 엔티티는 각 컨텍스트의 adapter.outbound에 둘
    //      것이라 아직 없다 — 지금은 접속·마이그레이션·스키마 검증(ddl-auto=validate) 기반만 올린다.
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    // Flyway: ADR 0004로 DDL 소유가 Kotlin(Flyway)이 되었다. Boot 4는 Flyway 자동 설정이 별도 스타터이고,
    // PostgreSQL 지원은 flyway-database-postgresql 모듈에 있다(Flyway 10+).
    implementation("org.springframework.boot:spring-boot-starter-flyway")
    implementation("org.flywaydb:flyway-database-postgresql")
    runtimeOnly("org.postgresql:postgresql")
    // PostGIS geometry 컬럼(position, geom, route)을 JPA 엔티티에 매핑하기 위한 Hibernate 공간 확장
    implementation("org.hibernate.orm:hibernate-spatial")

    // --- 보안 골격 (Unit 2-4) ----------------------------------------------------------
    // 인증·인가 뼈대. 단, 기본 설정에서는 어떤 경로도 보호하지 않는다 — legacy에 인증이 없어서
    // Kotlin만 인증을 요구하면 Golden Replay로 양쪽을 비교할 수 없기 때문(SecurityConfig 주석, ADR 0006).
    implementation("org.springframework.boot:spring-boot-starter-security")
    // JWT를 검증하는 리소스 서버. 토큰 발급은 외부 OIDC 공급자가 하고 우리는 검증만 한다(8단계에서 연동).
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")

    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
    // ApplicationModules.verify()·모듈 문서 생성 등 시험용 지원
    testImplementation("org.springframework.modulith:spring-modulith-starter-test")
    // 모듈 "안"의 레이어 규칙(domain이 Spring을 모른다 등)을 코드로 검사한다
    testImplementation("com.tngtech.archunit:archunit-junit5:$archunitVersion")
    // 실제 PostgreSQL/PostGIS 컨테이너로 마이그레이션 게이트를 시험한다(mock DB로는 Flyway·PostGIS를 검증할 수 없다)
    testImplementation("org.springframework.boot:spring-boot-testcontainers")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter")
    testImplementation("org.testcontainers:testcontainers-postgresql")
    // 보안을 켰을 때 "실제로 막히는지"를 시험하기 위한 지원(가짜 JWT 주입 등)
    testImplementation("org.springframework.security:spring-security-test")
}
