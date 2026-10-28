package com.aeroops.c2

import jakarta.validation.Valid
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotBlank
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest
import org.springframework.context.annotation.Import
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get
import org.springframework.test.web.servlet.post
import org.springframework.validation.annotation.Validated
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import kotlin.test.Test

/** 시험용 요청 본문. legacy의 `TelemetryFrame`처럼 필수 필드와 범위 제약을 가진다. */
data class SampleBody(
    @field:NotBlank val assetId: String,
    @field:Min(0) val sequenceNo: Long,
)

/**
 * 오류 상황을 일으키기 위한 시험 전용 컨트롤러.
 *
 * 왜 필요한가: 실제 업무 컨트롤러는 3단계부터 생긴다. 하지만 오류 계약은 지금 고정해야 이후 컨트롤러들이
 * 같은 규칙을 따른다. 이 클래스는 test 소스셋에만 있으므로 실제 앱에는 등록되지 않는다.
 */
@RestController
@Validated
class ErrorFixtureController {
    /** 업무 오류: 어댑터가 도메인 예외를 [ApiErrorException]으로 바꿔 던지는 상황을 흉내낸다. */
    @GetMapping("/test-errors/business/{code}")
    fun business(@PathVariable code: Int): Nothing =
        throw ApiErrorException(HttpStatus.valueOf(code), "테스트 업무 오류 $code")

    /** 본문 검증: `@Valid`가 붙은 요청 본문. */
    @PostMapping("/test-errors/body")
    fun body(@RequestBody @Valid request: SampleBody): SampleBody = request

    /** 파라미터 검증(경로 1): `@Validated` + AOP → `ConstraintViolationException`. */
    @GetMapping("/test-errors/parameter")
    fun parameter(@RequestParam @Min(1) limit: Int): Int = limit
}

/**
 * 파라미터 검증의 **두 번째 경로**를 확인하기 위한 컨트롤러 — `@Validated`가 **없다**.
 *
 * 왜 따로 두나: 같은 "파라미터 제약 위반"인데 `@Validated` 유무에 따라 Spring이 던지는 예외가 다르다
 * (`ConstraintViolationException` vs `HandlerMethodValidationException`). 앞으로 만들 컨트롤러가 어느 쪽을
 * 쓰든 같은 422 응답이 나와야 하므로, 두 경로를 각각 시험한다([ApiErrorHandler]의 두 핸들러).
 */
@RestController
class PlainParameterFixtureController {
    @GetMapping("/test-errors/plain-parameter")
    fun parameter(@RequestParam @Min(1) limit: Int): Int = limit
}

/**
 * [ApiErrorHandler]가 **legacy FastAPI와 같은 모양**의 오류 응답을 내는지 확인한다.
 *
 * 왜 `@WebMvcTest`인가: 오류 변환은 웹 레이어의 일이라 DB·Flyway까지 띄울 필요가 없다. 전체 컨텍스트를
 * 띄우는 `@SpringBootTest`를 쓰면 DB 컨테이너가 있어야 해서 느리고, 이 시험의 관심사와도 멀다.
 *
 * 확인하는 계약(근거: `tests/contracts/baseline/openapi.json`의 422, `frontend/src/api/client.ts`):
 * - 업무 오류 → 지정한 상태 코드 + `{"detail": "문자열"}` (프론트가 그대로 화면에 쓰는 형식)
 * - 검증 실패 → **422** + `{"detail": [{loc, msg, type}]}` (Spring 기본값 400이 아니다)
 *
 * 연관 코드: [ApiErrorHandler], [ErrorResponse]·[ApiErrorException](ApiError.kt),
 * legacy 원본 `legacy-backend/app/modules/<모듈>/router.py`의 `HTTPException`.
 */
@WebMvcTest(controllers = [ErrorFixtureController::class, PlainParameterFixtureController::class])
@Import(ApiErrorHandler::class)
class ApiErrorContractTest(@Autowired private val mockMvc: MockMvc) {

    // --- 업무 오류: 상태 코드 + detail 문자열 ------------------------------------------------

    @Test
    fun `업무 오류는 지정한 상태 코드와 detail 문자열을 낸다`() {
        // Golden Replay의 명령 흐름에 실제로 나오는 코드들(403 본인 승인 거부, 404, 409 충돌)
        listOf(403, 404, 409).forEach { code ->
            mockMvc.get("/test-errors/business/$code").andExpect {
                status { isEqualTo(code) }
                content { contentType(MediaType.APPLICATION_JSON) }
                jsonPath("$.detail") { value("테스트 업무 오류 $code") } // 배열이 아닌 문자열이어야 한다
            }
        }
    }

    // --- 검증 실패: 422 + detail 배열 -------------------------------------------------------

    @Test
    fun `본문 제약 위반은 400이 아니라 422를 낸다`() {
        mockMvc.post("/test-errors/body") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"assetId":"","sequenceNo":-1}"""
        }.andExpect {
            status { isUnprocessableContent() } // Spring 기본값은 400 — legacy에 맞춰 422여야 한다
            jsonPath("$.detail") { isArray() }
            jsonPath("$.detail.length()") { value(2) } // assetId(공백)와 sequenceNo(-1) 두 건
            jsonPath("$.detail[0].loc[0]") { value("body") }
            jsonPath("$.detail[0].msg") { exists() }
            jsonPath("$.detail[0].type") { exists() }
        }
    }

    @Test
    fun `필수 필드가 빠지면 422와 함께 어느 필드인지 알려준다`() {
        mockMvc.post("/test-errors/body") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"sequenceNo":1}""" // assetId 없음 — Kotlin non-null 필드라 역직렬화 단계에서 실패
        }.andExpect {
            status { isUnprocessableContent() }
            jsonPath("$.detail[0].loc[0]") { value("body") }
            jsonPath("$.detail[0].loc[1]") { value("assetId") } // Jackson이 알려준 경로가 담긴다
        }
    }

    @Test
    fun `깨진 JSON도 422를 낸다`() {
        mockMvc.post("/test-errors/body") {
            contentType = MediaType.APPLICATION_JSON
            content = "{ not json"
        }.andExpect {
            status { isUnprocessableContent() }
            jsonPath("$.detail") { isArray() }
        }
    }

    @Test
    fun `파라미터 타입 불일치는 422를 낸다`() {
        mockMvc.get("/test-errors/parameter?limit=abc").andExpect {
            status { isUnprocessableContent() }
            jsonPath("$.detail[0].loc[0]") { value("query") }
            jsonPath("$.detail[0].loc[1]") { value("limit") }
        }
    }

    @Test
    fun `파라미터 제약 위반은 422를 낸다 - Validated AOP 경로`() {
        mockMvc.get("/test-errors/parameter?limit=0").andExpect { // @Min(1) 위반
            status { isUnprocessableContent() }
            jsonPath("$.detail") { isArray() }
            jsonPath("$.detail[0].loc[0]") { value("query") }
            jsonPath("$.detail[0].loc[1]") { value("limit") }
        }
    }

    @Test
    fun `파라미터 제약 위반은 422를 낸다 - Spring 내장 검증 경로`() {
        // @Validated가 없는 컨트롤러 — Spring MVC가 HandlerMethodValidationException을 던진다.
        // 예외 종류가 달라도 같은 응답 계약이어야 한다.
        mockMvc.get("/test-errors/plain-parameter?limit=0").andExpect {
            status { isUnprocessableContent() }
            jsonPath("$.detail") { isArray() }
            jsonPath("$.detail[0].loc[0]") { value("query") }
            jsonPath("$.detail[0].loc[1]") { value("limit") }
        }
    }

    @Test
    fun `정상 요청은 그대로 통과한다(핸들러가 성공 경로를 가로채지 않는다)`() {
        mockMvc.post("/test-errors/body") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"assetId":"drone-01","sequenceNo":0}"""
        }.andExpect {
            status { isOk() }
            jsonPath("$.assetId") { value("drone-01") }
        }
    }
}
