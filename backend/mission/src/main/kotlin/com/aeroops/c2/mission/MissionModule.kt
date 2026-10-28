package com.aeroops.c2.mission

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * Spring Modulith에게 이 패키지가 하나의 애플리케이션 모듈(경계 컨텍스트)임을 알리는 메타데이터.
 *
 * 왜 클래스인가: Java는 `package-info.java`에 모듈 어노테이션을 달지만 Kotlin에는 그 파일이 없다.
 * Modulith가 Kotlin용으로 제공하는 `@PackageInfo` 클래스가 같은 역할을 한다.
 *
 * 목적: ① 이 모듈의 이름("mission")과 표시명을 정한다. ② `allowedDependencies`로 이 모듈이 의존해도
 * 되는 모듈을 명시한다 — 비어 있으면 **다른 어떤 컨텍스트에도 의존할 수 없다**(shared 제외).
 * Mission Operations는 Command & Control의 상류라서 의존 대상이 없다(docs/planning/10 §4).
 *
 * 연관 코드:
 * - 검증: bootstrap의 `ModularityTest`가 이 선언을 실제 import와 대조한다.
 * - Gradle 의존성: `mission/build.gradle.kts` (선언과 일치해야 한다).
 * - 이 모듈의 공개 API는 이 패키지(`com.aeroops.c2.mission`) 최상위 타입이고, `domain`·`application`·
 *   `adapter` 하위 패키지는 모듈 내부라서 다른 모듈이 접근하면 Modulith 검증이 실패한다.
 */
@PackageInfo
@ApplicationModule(displayName = "Mission Operations", allowedDependencies = [])
class MissionModule
