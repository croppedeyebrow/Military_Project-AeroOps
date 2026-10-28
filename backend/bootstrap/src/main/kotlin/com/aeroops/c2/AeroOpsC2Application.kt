package com.aeroops.c2

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.modulith.Modulithic

/**
 * Kotlin C2 Core 진입점(ADR 0004). 전환 기간에는 legacy FastAPI(8000)와 나란히 떠야 하므로
 * 포트를 8080으로 분리한다(`application.yml`).
 *
 * `@Modulithic(sharedModules = ["shared"])`의 이유: Spring Modulith는 `com.aeroops.c2` 바로 아래
 * 패키지를 각각 하나의 모듈로 본다. shared-kernel(`com.aeroops.c2.shared`)도 그중 하나로 잡히는데,
 * 이것은 업무 컨텍스트가 아니라 모두가 쓰는 값 객체 모음(AssetId, BootId …)이다. "shared"를 공유
 * 모듈로 지정하면 모든 컨텍스트가 `allowedDependencies`에 일일이 적지 않아도 이를 쓸 수 있다.
 * (어노테이션을 shared-kernel이 아니라 여기 둔 것은 shared-kernel을 프레임워크 비의존 순수 Kotlin으로
 * 유지하기 위해서다.)
 *
 * 연관 코드: 모듈 검증은 `ModularityTest`, 각 컨텍스트의 `*Module.kt`(allowedDependencies),
 * 공유 커널은 shared-kernel 모듈.
 */
@SpringBootApplication
@Modulithic(sharedModules = ["shared"])
class AeroOpsC2Application

fun main(args: Array<String>) {
    runApplication<AeroOpsC2Application>(*args)
}
