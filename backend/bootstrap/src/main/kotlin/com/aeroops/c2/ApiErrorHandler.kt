package com.aeroops.c2

import jakarta.validation.ConstraintViolationException
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.http.converter.HttpMessageNotReadableException
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.method.annotation.HandlerMethodValidationException
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException
import tools.jackson.databind.exc.MismatchedInputException

/**
 * 모든 컨트롤러의 예외를 legacy FastAPI와 **같은 모양의 HTTP 응답**으로 바꾼다.
 *
 * 왜 필요한가(근거): Spring의 기본 오류 응답은 RFC 9457 ProblemDetail이고 검증 실패는 400이다. legacy는
 * `{"detail": ...}` 형식에 검증 실패가 **422**다. React는 legacy 계약에 맞춰져 있고(`frontend/src/api/client.ts`),
 * 계약 기준선(`tests/contracts/baseline/openapi.json`)에도 422가 29곳 박혀 있다. 전환 중에는 Kotlin이 legacy
 * 계약을 그대로 따라야 프론트를 고치지 않고 갈아끼울 수 있다(ADR 0004).
 *
 * 목적: 예외 → (상태 코드, 본문) 매핑을 한 곳에 모아, 각 컨트롤러가 오류 형식을 따로 신경 쓰지 않게 한다.
 *
 * 매핑 규칙:
 * | 예외 | 상태 | 본문 | legacy에서 같은 상황 |
 * |---|---|---|---|
 * | [ApiErrorException] | 지정한 코드 | `{"detail": "메시지"}` | `HTTPException(status_code, detail)` |
 * | 본문 검증 실패·파싱 실패 | 422 | `{"detail": [{loc,msg,type}]}` | Pydantic `RequestValidationError` |
 * | 쿼리·경로 파라미터 오류 | 422 | 같음 | 같음 |
 *
 * 연관 코드: 응답 타입과 예외 정의는 [ApiError.kt][ErrorResponse], 시험은 `ApiErrorContractTest`
 * (legacy 계약과 같은 모양인지 확인), legacy 원본은 각 모듈의 `legacy-backend/app/modules/<모듈>/router.py`.
 *
 * 패키지 위치: Modulith가 `com.aeroops.c2` 바로 아래 하위 패키지를 업무 모듈로 보기 때문에, 인프라 성격인
 * 이 클래스는 루트 패키지에 둔다(`FlywayMigrationConfig`와 같은 이유).
 */
@RestControllerAdvice
class ApiErrorHandler {

    /** 어댑터가 도메인 예외를 바꿔 던진 업무 오류. 상태 코드는 던진 쪽이 정한다. */
    @ExceptionHandler(ApiErrorException::class)
    fun handleApiError(exception: ApiErrorException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(exception.status).body(ErrorResponse(exception.message))

    /** `@Valid` 본문 검증 실패(필드 제약 위반). 필드마다 한 항목을 만든다. */
    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleBodyValidation(exception: MethodArgumentNotValidException): ResponseEntity<ValidationErrorResponse> {
        val items = exception.bindingResult.fieldErrors.map { error ->
            ValidationErrorItem(
                loc = listOf(BODY) + error.field.split("."),
                msg = error.defaultMessage ?: "유효하지 않은 값",
                // 제약 어노테이션 이름(NotNull, Min …)을 소문자로. legacy의 Pydantic 타입 문자열과 값은
                // 다르지만 프론트가 쓰지 않는 필드다(ApiError.kt의 ValidationErrorItem 설명).
                type = (error.code ?: "invalid").lowercase(),
            )
        }
        return unprocessable(items)
    }

    /**
     * 요청 본문을 읽지 못한 경우 — 깨진 JSON, 타입 불일치, Kotlin의 non-null 필드 누락 등.
     *
     * Jackson이 어느 위치에서 실패했는지 알고 있으면([MismatchedInputException.path]) 그 경로를 `loc`에 담아
     * "어느 필드가 문제인지"를 legacy와 비슷하게 알려준다. 모르면 `["body"]`까지만 담는다.
     */
    @ExceptionHandler(HttpMessageNotReadableException::class)
    fun handleUnreadableBody(exception: HttpMessageNotReadableException): ResponseEntity<ValidationErrorResponse> {
        val cause = exception.cause
        val location = if (cause is MismatchedInputException) {
            listOf(BODY) + cause.path.mapNotNull { it.propertyName }
        } else {
            listOf(BODY)
        }
        return unprocessable(
            listOf(
                ValidationErrorItem(
                    loc = location,
                    msg = cause?.message?.lineSequence()?.firstOrNull() ?: "본문을 읽을 수 없다",
                    type = "value_error",
                ),
            ),
        )
    }

    /** 경로 변수·쿼리 파라미터의 타입이 맞지 않는 경우(예: 숫자 자리에 문자). */
    @ExceptionHandler(MethodArgumentTypeMismatchException::class)
    fun handleTypeMismatch(exception: MethodArgumentTypeMismatchException): ResponseEntity<ValidationErrorResponse> =
        unprocessable(
            listOf(
                ValidationErrorItem(
                    loc = listOf(PARAMETER, exception.name),
                    msg = "'${exception.value}'는 올바른 값이 아니다",
                    type = "type_error",
                ),
            ),
        )

    /**
     * `@Validated`가 붙은 컨트롤러에서 AOP 메서드 검증이 걸린 경우.
     *
     * 왜 [HandlerMethodValidationException]과 **둘 다** 처리하나: 같은 "파라미터 제약 위반"인데 Spring이 던지는
     * 예외가 두 가지다. 클래스에 `@Validated`를 붙이면 AOP 프록시가 [ConstraintViolationException]을 던지고,
     * 붙이지 않으면 Spring MVC 내장 검증이 [HandlerMethodValidationException]을 던진다. 앞으로 만들 컨트롤러가
     * 어느 쪽을 쓸지 강제하지 않기 위해 두 경로를 모두 같은 422 응답으로 모은다(시험이 두 경우를 다 확인한다).
     */
    @ExceptionHandler(ConstraintViolationException::class)
    fun handleConstraintViolation(exception: ConstraintViolationException): ResponseEntity<ValidationErrorResponse> {
        val items = exception.constraintViolations.map { violation ->
            // propertyPath는 "메서드명.파라미터명" 형태다 — 마지막 조각이 파라미터 이름이다.
            val parameterName = violation.propertyPath.last()?.name ?: "unknown"
            ValidationErrorItem(
                loc = listOf(PARAMETER, parameterName),
                msg = violation.message,
                type = violation.constraintDescriptor.annotation.annotationClass.simpleName
                    ?.lowercase() ?: "invalid",
            )
        }
        return unprocessable(items)
    }

    /** 컨트롤러 메서드 파라미터의 제약 위반(예: `@RequestParam @Min(1) limit`). */
    @ExceptionHandler(HandlerMethodValidationException::class)
    fun handleParameterValidation(exception: HandlerMethodValidationException): ResponseEntity<ValidationErrorResponse> {
        val items = exception.parameterValidationResults.flatMap { result ->
            result.resolvableErrors.map { error ->
                ValidationErrorItem(
                    loc = listOf(PARAMETER, result.methodParameter.parameterName ?: "unknown"),
                    msg = error.defaultMessage ?: "유효하지 않은 값",
                    type = (error.codes?.firstOrNull() ?: "invalid").lowercase(),
                )
            }
        }
        return unprocessable(items)
    }

    private fun unprocessable(items: List<ValidationErrorItem>) =
        ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(ValidationErrorResponse(items))

    private companion object {
        /** legacy(FastAPI)가 `loc`의 첫 조각으로 쓰는 값. 본문 오류는 "body", 파라미터 오류는 "query"/"path". */
        const val BODY = "body"
        const val PARAMETER = "query"
    }
}
