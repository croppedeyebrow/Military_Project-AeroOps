package com.aeroops.c2

import org.springframework.http.HttpStatus

/**
 * HTTP 오류 응답의 모양과, 어댑터가 그것을 만들기 위해 던지는 예외.
 *
 * 왜 이 파일이 있나(근거): Kotlin C2 Core는 legacy FastAPI와 **같은 계약**을 내야 React를 고치지 않고
 * 갈아끼울 수 있다(ADR 0004, tests/contracts/baseline). legacy의 오류 응답은 두 가지 모양이다.
 *  - 업무 오류(403·404·409 등): `{"detail": "사람이 읽을 메시지"}`  ← 프론트가 그대로 화면에 쓴다
 *    (`frontend/src/api/client.ts`: detail이 문자열일 때만 에러 메시지로 사용)
 *  - 검증 실패(422): `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`  ← 프론트는 상태 코드만 본다
 * Spring MVC의 기본 오류 응답은 모양도 다르고 검증 실패가 400이라, 그대로 두면 계약이 깨진다.
 *
 * 연관 코드: 변환은 [ApiErrorHandler], 계약 근거는 `tests/contracts/baseline/openapi.json`(422 29곳)과
 * Golden Replay의 명령 흐름(403·409), 프론트 소비 지점은 `frontend/src/api/client.ts`.
 */

/** 업무 오류 응답 본문. `detail`이 **문자열**이라는 점이 프론트 계약의 핵심이다. */
data class ErrorResponse(val detail: String)

/**
 * 검증 실패(422) 응답 본문의 항목 한 건.
 *
 * `loc`는 오류가 난 위치를 조각으로 나눈 배열이다(legacy 예: `["body", "latitude"]`). `type`은 legacy가
 * Pydantic 오류 종류(`missing`, `greater_than_equal` …)를 쓰는데, Spring의 제약 이름과 1:1로 맞지 않는다.
 * 프론트가 이 값을 쓰지 않으므로(위 docstring) **구조만 동일하게** 맞추고 값은 Spring 기준으로 둔다.
 */
data class ValidationErrorItem(val loc: List<String>, val msg: String, val type: String)

/** 검증 실패 응답 본문. `detail`이 **배열**이라는 점이 업무 오류와 다르다. */
data class ValidationErrorResponse(val detail: List<ValidationErrorItem>)

/**
 * 어댑터(adapter.inbound)가 던지는 업무 오류. [ApiErrorHandler]가 받아 `{"detail": message}`로 바꾼다.
 *
 * 왜 도메인 예외를 그대로 쓰지 않나: 도메인은 HTTP를 몰라야 한다(ArchUnit `LayeringRules.domainIsFrameworkFree`).
 * 그래서 도메인 예외 → HTTP 상태 매핑은 각 컨텍스트의 adapter.inbound가 하고, 이 타입으로 바꿔 던진다.
 *
 * 사용 예(3·4단계에서 생길 모습):
 * ```
 * try { useCase.approve(id, by) }
 * catch (e: CommandNotFound) { throw ApiErrorException(HttpStatus.NOT_FOUND, e.message) }
 * ```
 * legacy의 대응 코드: `legacy-backend/app/modules/command/router.py`의 `HTTPException(status_code=..., detail=...)`.
 */
class ApiErrorException(
    val status: HttpStatus,
    override val message: String,
) : RuntimeException(message)
