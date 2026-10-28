package com.aeroops.c2

import com.tngtech.archunit.lang.ArchRule
import com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses

/**
 * 모듈 "안"의 레이어 규칙 정의 모음(ArchUnit).
 *
 * 왜 한 곳에 모으나: 같은 규칙을 ① 실제 코드(`LayeringRulesTest`의 실제 코드 검사)와 ② 위반 샘플
 * (`archfixture.layering.*`, 규칙이 실제로 위반을 잡는지 증명)에 똑같이 적용해야 한다. 규칙이 두 곳에
 * 복붙돼 있으면 한쪽만 고쳐져 "샘플에서는 잡히는데 실제 코드에는 다른 규칙이 적용되는" 일이 생긴다.
 *
 * 목적: docs/planning/02_백엔드_아키텍처.md의 의존 방향 — `adapter → application → domain` — 을 코드로
 * 고정한다. 모듈 "사이"의 경계(다른 모듈의 내부 접근·순환·미선언 의존)는 Modulith가 담당하고
 * (`ModularityTest`), 이 파일은 모듈 "안"의 레이어를 담당한다. 둘은 서로 다른 것을 본다.
 *
 * 패키지 패턴 `..domain..`은 "경로 어디든 domain 세그먼트가 있는 패키지"를 뜻한다. 실제 코드의
 * `com.aeroops.c2.operationalpicture.domain`과 샘플의 `archfixture.layering.baddomain.domain`에 모두
 * 맞게 하려고 모듈 이름을 패턴에 넣지 않았다.
 *
 * 연관 코드: `LayeringRulesTest`(실행), 실제 domain 코드의 첫 사례는 `operationalpicture/domain/ObservationKey`.
 */
object LayeringRules {
    /** domain이 의존하면 안 되는 프레임워크 패키지들. 순수 Kotlin 규칙을 유지하려는 것(JPA·웹·직렬화 포함). */
    private val FRAMEWORK_PACKAGES = arrayOf(
        "org.springframework..",
        "jakarta..",
        "javax..",
        "tools.jackson..",
        "com.fasterxml..",
    )

    /**
     * domain은 프레임워크를 모르고, 바깥 레이어(application·adapter)도 모른다.
     * 근거: 도메인 규칙이 Spring·JPA에 묶이면 단위 시험이 컨텍스트 기동을 요구하게 되고, 저장소를 바꿀 때
     * 업무 규칙까지 흔들린다. 의존 방향이 domain으로 모이게 하는 것이 구조의 핵심이다.
     */
    val domainIsFrameworkFree: ArchRule =
        noClasses().that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(*FRAMEWORK_PACKAGES)
            .orShould().dependOnClassesThat().resideInAnyPackage("..application..", "..adapter..")
            .because("domain은 Spring·JPA 같은 프레임워크와 바깥 레이어를 모르는 순수 Kotlin이어야 한다")
            .allowEmptyShould(true)

    /**
     * application은 adapter 구현을 직접 쥐지 않는다(포트 인터페이스를 통해서만 만난다).
     * 근거: 유스케이스가 `JpaStore` 같은 구현에 의존하면 저장소 교체·시험 대역 주입이 막힌다. 포트는
     * application이 정의하고 adapter가 구현하는 것이 의존 역전의 핵심이다.
     */
    val applicationDoesNotDependOnAdapters: ArchRule =
        noClasses().that().resideInAPackage("..application..")
            .should().dependOnClassesThat().resideInAPackage("..adapter..")
            .because("application은 adapter 구현이 아니라 포트(인터페이스)에 의존해야 한다")
            .allowEmptyShould(true)

    /**
     * inbound 어댑터(컨트롤러·메시지 수신)와 outbound 어댑터(저장소·외부 호출)는 서로 모른다.
     * 근거: 둘이 직접 만나면 application·domain의 규칙(검증, 트랜잭션, 정책)을 우회하는 지름길이 생긴다.
     */
    val inboundAndOutboundAdaptersAreIndependent: ArchRule =
        noClasses().that().resideInAPackage("..adapter.inbound..")
            .should().dependOnClassesThat().resideInAPackage("..adapter.outbound..")
            .because("inbound 어댑터는 outbound 어댑터를 직접 호출하지 않고 application을 거쳐야 한다")
            .allowEmptyShould(true)

    /** 위 규칙들의 이름과 정의(시험에서 반복 실행하기 위함). */
    val all: Map<String, ArchRule> = mapOf(
        "domainIsFrameworkFree" to domainIsFrameworkFree,
        "applicationDoesNotDependOnAdapters" to applicationDoesNotDependOnAdapters,
        "inboundAndOutboundAdaptersAreIndependent" to inboundAndOutboundAdaptersAreIndependent,
    )
}
