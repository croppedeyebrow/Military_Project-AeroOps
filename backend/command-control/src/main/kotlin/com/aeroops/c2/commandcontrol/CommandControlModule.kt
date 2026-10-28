package com.aeroops.c2.commandcontrol

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * "Command & Control" 경계 컨텍스트의 Modulith 모듈 메타데이터(구조 설명은 MissionModule.kt 참고).
 *
 * 목적: 명령의 생성·승인·전달·ACK·실행·효과 검증 수명주기와 통제권(ControlLease)을 소유한다.
 *
 * `allowedDependencies`가 4개인 이유(하류 컨텍스트): mission(어느 임무의 명령인가), safetypolicy(허용 판정),
 * operationalpicture(대상 기체 신선도), audit(감사 기록). 여기 적히지 않은 모듈(예: incident)을 이 모듈이
 * import하면 Modulith 검증이 실패한다 — 명령 처리에 경보 규칙이 섞이는 것을 막으려는 것이다.
 * 모듈 이름은 대상 패키지의 마지막 이름(`com.aeroops.c2.<이름>`)이다.
 *
 * 연관 코드:
 * - Gradle 의존성: `command-control/build.gradle.kts`(같은 4개).
 * - 검증: bootstrap `ModularityTest`(허용 목록을 시험에서 고정하고 위반 샘플로 실제로 막히는지 확인).
 * - 이관 비교 기준: Golden Replay의 commands 9종(tests/contracts/golden), 불변조건 1~8(docs/planning/13 §4).
 */
@PackageInfo
@ApplicationModule(
    displayName = "Command & Control",
    allowedDependencies = ["mission", "safetypolicy", "operationalpicture", "audit"],
)
class CommandControlModule
