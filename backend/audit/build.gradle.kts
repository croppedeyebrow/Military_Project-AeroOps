/*
 * audit 모듈 — 경계 컨텍스트 "Identity & Audit" 중 불변 감사 기록 부분.
 *
 * 왜 의존성이 shared-kernel뿐인가: 감사는 모든 컨텍스트가 호출하는 "공개 서비스(Open Host)"다.
 *   감사가 다른 컨텍스트를 알기 시작하면 모든 컨텍스트와 순환하게 된다. 그래서 감사는 누가·무엇을·언제만
 *   받고, 그것이 어느 업무에서 왔는지는 모르는 중립 어휘(문자열 target_type 등)로만 다룬다.
 * 연관: AuditModule.kt, 사용처는 command-control·incident. 현행 대응은 legacy-backend의 audit 모듈
 *       (audit_logs 테이블, docs/planning/13 §2). users·roles(인증)는 2-4 Security 단계에서 추가한다.
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation("org.springframework.modulith:spring-modulith-api")
}
