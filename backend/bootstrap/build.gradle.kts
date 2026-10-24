// 실행·조립 모듈 — Spring Boot 앱의 진입점과 설정만 둔다. 업무 규칙은 두지 않는다(각 경계 컨텍스트 모듈이 소유).
plugins {
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.kotlin.spring) // @Component 등 Spring 어노테이션 클래스를 자동으로 open 처리
}

dependencies {
    implementation(project(":shared-kernel"))

    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    // Spring Boot 4는 Jackson 3(패키지 tools.jackson)을 쓴다 — Kotlin data class 직렬화에 필요
    implementation("tools.jackson.module:jackson-module-kotlin")

    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
}
