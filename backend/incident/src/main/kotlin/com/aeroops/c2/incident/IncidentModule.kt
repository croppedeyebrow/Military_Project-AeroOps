package com.aeroops.c2.incident

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * "Incident Management" 경계 컨텍스트의 Modulith 모듈 메타데이터(구조 설명은 MissionModule.kt 참고).
 *
 * 목적: 규칙이 만든 경보와 그 확인·해제·중복 억제, 이후 사건(Incident) 단위 상관관계를 소유한다.
 *
 * `command-control`이 목록에 없는 이유: 경보 판정은 명령 처리와 독립이어야 한다(예: 명령 모듈이 멈춰도
 * 배터리 경보는 나와야 한다). 이 독립성을 "import 금지"로 고정했다.
 *
 * 연관 코드: Gradle 의존성 `incident/build.gradle.kts`, 검증은 bootstrap `ModularityTest`,
 * 이관 비교 기준은 Golden Replay의 alerts(battery_low 시나리오), 현행 규칙은 legacy-backend의
 * `alert/rules.py`(배터리·RSSI·지오펜스).
 */
@PackageInfo
@ApplicationModule(
    displayName = "Incident Management",
    allowedDependencies = ["operationalpicture", "safetypolicy", "mission", "audit"],
)
class IncidentModule
