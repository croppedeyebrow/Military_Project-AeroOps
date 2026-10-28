/*
 * safety-policy 모듈 — 경계 컨텍스트 "Safety & Policy"(지오펜스·Failsafe 정책·정책 버전).
 *
 * 왜 의존성이 shared-kernel뿐인가: Safety & Policy는 Command & Control에 "버전이 붙은 허용 판정"을
 *   공급하는 상류(Customer/Supplier, docs/planning/10 §4)다. 정책이 명령 모듈을 알면 "명령이 이미
 *   있으니 허용" 같은 역방향 결합이 생겨 안전 판정이 오염된다.
 * 연관: SafetyPolicyModule.kt의 allowedDependencies, 사용처는 command-control·incident.
 *       현행 대응 테이블은 geofences(legacy-backend의 mission 모듈이 쥐고 있던 것을 이관, docs/planning/13 §2).
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation("org.springframework.modulith:spring-modulith-api")
}
