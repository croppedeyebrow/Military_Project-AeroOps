/*
 * command-control 모듈 — 경계 컨텍스트 "Command & Control"(명령 수명주기·승인·통제권·효과 검증).
 *
 * 왜 의존성이 4개인가: Context Map(docs/planning/10 §4, docs/planning/13 §2)에서 이 컨텍스트는 여러
 *   상류의 "하류"다. 명령을 내리려면
 *   - mission: 어느 임무·단계에 대한 명령인지(Published Language: mission/phase ID)
 *   - safety-policy: 버전이 붙은 허용 판정(Dispatch 직전 재검증, 불변조건 4번)
 *   - operational-picture: 대상 기체 관측의 신선도(오래된 상태로 위험 명령을 내리지 않기 위해)
 *   - audit: 승인·취소 등 모든 전이를 불변 기록으로 남기기 위해
 *   를 알아야 한다. 반대 방향(이들이 명령 모듈을 아는 것)은 허용하지 않는다.
 * 연관: CommandControlModule.kt의 allowedDependencies와 아래 project(...) 의존성은 항상 같아야 한다.
 *       현행 대응은 legacy-backend/app/modules/command(상태 머신 `state_machine.py` 등).
 *       이 모듈이 소유할 테이블: commands, command_events (control_leases는 Kotlin 4단계 신규).
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation(project(":mission"))
    implementation(project(":safety-policy"))
    implementation(project(":operational-picture"))
    implementation(project(":audit"))
    implementation("org.springframework.modulith:spring-modulith-api")
}
