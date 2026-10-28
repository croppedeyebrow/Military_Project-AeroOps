package com.aeroops.c2.audit

/**
 * 운용자의 역할 — 누가 무엇을 할 수 있는지의 기준.
 *
 * 왜 Identity & Audit 컨텍스트에 있나(근거): 역할은 "이 사람이 누구인가"에 속하는 어휘다
 * (docs/planning/10 §4의 Identity & Audit, docs/planning/13 §2). 명령 모듈이 자기만의 역할 개념을
 * 따로 두면 컨텍스트마다 권한 해석이 갈라진다. 그래서 한 곳에서 정의하고, 필요한 컨텍스트가 가져다 쓴다
 * (`command-control`·`incident`는 이미 이 모듈에 의존한다).
 *
 * 목적: 문자열("operator") 대신 타입으로 다뤄 오타·미정의 역할을 컴파일 시점에 막는다.
 *
 * 역할 구분의 근거(docs/new_roadmap/08_통합검증_Cutover_Day14.md, planning/08): 운영자는 명령을 요청하고,
 * **승인자는 요청자와 달라야 하며**(불변조건: 요청자 본인 승인 금지 — Golden Replay `self_approve`가 403),
 * 분석자는 조회만, 관리자는 설정·정책을 다룬다.
 *
 * 연관 코드: Spring 권한 문자열로의 변환은 [authority], JWT 클레임 → 권한 매핑은 bootstrap의 `SecurityConfig`,
 * 실제 권한 검사(`@PreAuthorize` 등)는 각 컨텍스트의 adapter.inbound가 3·4단계에서 붙인다.
 */
enum class OperationalRole {
    /** 임무·명령을 요청하고 기체를 운용한다. */
    OPERATOR,

    /** 요청된 명령을 승인한다(요청자와 같은 사람일 수 없다). */
    APPROVER,

    /** 상황도·이력·경보를 조회만 한다(쓰기 권한 없음). */
    ANALYST,

    /** 정책·구역·시스템 설정을 관리한다. */
    ADMIN,
    ;

    /**
     * Spring Security가 쓰는 권한 문자열(`ROLE_` 접두사 규칙).
     *
     * 왜 접두사를 붙이나: `hasRole("OPERATOR")`는 내부적으로 `ROLE_OPERATOR` 권한을 찾는다. 이 변환을
     * 한 곳에 두어 JWT 매핑과 권한 검사가 같은 문자열을 쓰도록 보장한다.
     */
    val authority: String get() = "ROLE_$name"

    companion object {
        /** JWT 클레임의 문자열을 역할로 바꾼다. 모르는 값은 null(무시) — 토큰에 낯선 역할이 있어도 기동을 막지 않는다. */
        fun fromClaim(value: String): OperationalRole? =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) }
    }
}
