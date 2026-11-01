/*
 * operational-picture 모듈 — 경계 컨텍스트 "Operational Picture"(관측·최신 상황·신선도/품질).
 *
 * 왜 의존성이 shared-kernel뿐인가: 장비 Wire 프레임을 도메인 관측으로 바꾼 사실을 쥐는 상류다.
 *   Incident(경보)·Command(Dispatch 직전 신선도 재검증)가 이 모듈을 읽는다. 상류가 하류를 알면
 *   "경보가 있으니 이 관측은 무시" 같은 역방향 영향이 생겨 상황도가 오염된다.
 * 연관: OperationalPictureModule.kt, 도메인 핵심은 domain/ObservationKey.kt(ADR 0005),
 *       현행 대응은 legacy-backend의 telemetry·ingestion·realtime 모듈(docs/planning/13 §2),
 *       이 모듈이 소유할 테이블: assets, telemetry_frames, asset_latest_state.
 */
plugins {
    id("java-library")
    // @Repository·@Transactional이 붙은 클래스를 Spring이 프록시로 감싸는데, Kotlin 클래스는 기본이
    // final이라 그대로 두면 프록시 생성이 실패한다(2-4에서 같은 문제를 겪었다).
    alias(libs.plugins.kotlin.spring)
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation("org.springframework.modulith:spring-modulith-api")

    // adapter 계층이 쓰는 Spring 모듈만 최소로 가져온다. starter(자동설정 포함)를 쓰지 않는 이유는
    // 이 모듈이 애플리케이션이 아니라 라이브러리이기 때문이다 — 조립은 bootstrap이 한다.
    // domain 패키지는 이들을 import하지 않는다(ArchUnit LayeringRules.domainIsFrameworkFree가 강제).
    implementation("org.springframework:spring-jdbc")
    implementation("org.springframework:spring-tx")
    implementation("org.springframework:spring-context")
    // Redis Stream 소비(3-4). legacy가 발행한 같은 스트림을 별도 consumer group으로 읽는다(ADR 0004).
    implementation("org.springframework.data:spring-data-redis")
    // @ConditionalOnProperty 등 조건부 빈 등록. 모듈이 자기 인프라 조립을 소유하므로 필요하다
    // (조립을 bootstrap에 두면 루트가 이 모듈의 내부 타입을 참조하게 되어 Modulith 검증에 걸린다).
    implementation("org.springframework.boot:spring-boot-autoconfigure")
    // Wire JSON(legacy TelemetryFrame) 역직렬화. Spring Boot 4는 Jackson 3(패키지 tools.jackson)을 쓰지만,
    // 어노테이션은 호환성을 위해 예전 패키지(com.fasterxml.jackson.annotation)에 그대로 있다.
    implementation("tools.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.core:jackson-annotations")
}
