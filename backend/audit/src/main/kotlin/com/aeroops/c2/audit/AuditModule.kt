package com.aeroops.c2.audit

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * "Identity & Audit" 경계 컨텍스트(이번 유닛에서는 감사 부분)의 Modulith 모듈 메타데이터.
 *
 * 목적: append-only 감사 기록을 소유한다. 다른 컨텍스트는 이 모듈의 공개 API로만 감사를 남기고,
 * `audit_logs` 테이블에 직접 쓰지 않는다(docs/planning/13 §2의 "교차 쓰기 금지").
 * 의존 대상이 없는 이유: 모든 컨텍스트가 호출하는 상류 서비스라서 역방향 의존이 순환을 만든다.
 *
 * 연관 코드: command-control·incident가 이 API를 사용(각 모듈의 allowedDependencies). 같은 문제의 현행
 * 사례는 legacy-backend의 `event_log`를 4개 모듈이 직접 INSERT하던 것(docs/planning/13 §2) —
 * 이 구조는 그런 직접 쓰기를 빌드 단계에서 막으려는 것이다.
 */
@PackageInfo
@ApplicationModule(displayName = "Identity & Audit", allowedDependencies = [])
class AuditModule
