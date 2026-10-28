package com.aeroops.c2.safetypolicy

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * "Safety & Policy" 경계 컨텍스트의 Modulith 모듈 메타데이터(구조 설명은 MissionModule.kt 참고).
 *
 * 목적: 정책 판정(허용/거부와 근거, 정책 버전)을 소유하고, 다른 컨텍스트에는 공개 API로만 제공한다.
 * 의존 대상이 없는 이유: 상류 컨텍스트라서 다른 컨텍스트를 알면 안 된다(docs/planning/10 §4).
 *
 * 연관 코드: command-control(Dispatch 직전 정책 재검증, docs/planning/13 불변조건 4번), incident(지오펜스
 * 이탈 규칙)이 이 모듈의 공개 API를 사용한다. 검증은 bootstrap의 `ModularityTest`.
 */
@PackageInfo
@ApplicationModule(displayName = "Safety & Policy", allowedDependencies = [])
class SafetyPolicyModule
