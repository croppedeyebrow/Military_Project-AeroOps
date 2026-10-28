package com.aeroops.c2

import com.aeroops.c2.audit.OperationalRole
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Import
import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.test.context.TestPropertySource
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import kotlin.test.Test
import kotlin.test.assertEquals

/**
 * 보안 설정이 **꺼졌을 때와 켜졌을 때 각각 의도대로 동작하는지** 확인한다.
 *
 * 왜 두 상태를 모두 시험하나(근거): [SecurityConfig]의 기본값은 "아무 경로도 보호하지 않음"이다
 * (legacy에 인증이 없어 Golden Replay 비교를 깨지 않기 위해 — ADR 0006). 이런 설계는 "보안을 넣었다"고
 * 착각하기 쉬운 위험이 있다. 그래서 ① 기본 상태에서 정말로 열려 있다는 것과, ② 켜면 정말로 막힌다는 것을
 * 둘 다 고정해 둔다. ②가 없으면 보안 코드가 사실은 동작하지 않아도 아무도 모른다.
 *
 * 연관 코드: [SecurityConfig], [OperationalRole](audit 모듈), 전환 전제는 ADR 0004·0006.
 */

/** 보호 대상을 흉내내는 시험 전용 컨트롤러(test 소스셋에만 있으므로 실제 앱에는 등록되지 않는다). */
@RestController
class ProtectedFixtureController {
    @GetMapping("/test-secure/open")
    fun open(): String = "ok"

    /** 승인자만 호출할 수 있는 자원 — 역할 기반 인가가 실제로 동작하는지 보기 위한 것. */
    @GetMapping("/test-secure/approver-only")
    @PreAuthorize("hasRole('APPROVER')")
    fun approverOnly(): String = "approved"
}

/**
 * 가짜 JWT 디코더 — 외부 OIDC 공급자 없이 리소스 서버 설정을 띄우기 위해 필요하다(실제 연동은 8단계).
 *
 * 토큰 값을 그대로 역할 목록으로 해석한다(예: `Bearer APPROVER` → `roles: ["APPROVER"]`, 여러 개는 `.`으로
 * 구분). 구분자가 쉼표가 아닌 이유: Bearer 토큰은 허용 문자가 정해져 있어 쉼표가 들어가면 Spring Security가
 * 토큰 형식 자체를 거부해 401이 된다(실제로 시험 중 확인). 이렇게 한 이유는
 * **디코더 → 역할 변환기 → 인가**로 이어지는 실제 경로를 전부 지나게 하기 위해서다. Spring Security Test의
 * `jwt()` 후처리기는 인증 토큰을 직접 만들어 넣기 때문에 [SecurityConfig]의 역할 변환기를 건너뛰고,
 * 그러면 정작 검증하려던 변환 규칙이 시험되지 않는다.
 */
class FakeJwtDecoderConfig {
    @Bean
    fun jwtDecoder(): JwtDecoder = JwtDecoder { token ->
        val roles = token.split(".").filter { it.isNotBlank() }
        Jwt.withTokenValue(token)
            .header("alg", "none")
            .subject("test-user")
            .claim("roles", roles)
            .build()
    }
}

/**
 * 기본 상태(보안 꺼짐) — 인증 없이 접근된다. 이것이 전환 기간의 의도된 동작이다.
 */
@WebMvcTest(controllers = [ProtectedFixtureController::class])
@Import(SecurityConfig::class)
class SecurityDisabledTest(@Autowired private val mockMvc: MockMvc) {

    @Test
    fun `보안이 꺼져 있으면 토큰 없이도 접근된다`() {
        mockMvc.get("/test-secure/open").andExpect { status { isOk() } }
    }

    @Test
    fun `보안이 꺼져 있으면 PreAuthorize가 붙은 경로도 열려 있다`() {
        // 메서드 보안을 항상 켜 두면 필터체인이 비보호여도 여기서 막혀 "기본은 비보호" 전제가 깨진다.
        // MethodSecurityConfig를 같은 스위치로 분리한 이유가 이것이다(SecurityConfig.kt 주석).
        mockMvc.get("/test-secure/approver-only").andExpect { status { isOk() } }
    }
}

/**
 * 보안을 켠 상태 — 토큰이 없으면 막히고, 역할이 맞아야 통과한다.
 */
@WebMvcTest(controllers = [ProtectedFixtureController::class])
@Import(SecurityConfig::class, MethodSecurityConfig::class, FakeJwtDecoderConfig::class)
@TestPropertySource(properties = ["aeroops.security.enabled=true"])
class SecurityEnabledTest(@Autowired private val mockMvc: MockMvc) {

    @Test
    fun `토큰이 없으면 401로 막힌다`() {
        mockMvc.get("/test-secure/open").andExpect { status { isUnauthorized() } }
    }

    @Test
    fun `유효한 토큰이면 통과한다`() {
        mockMvc.get("/test-secure/open") {
            header("Authorization", "Bearer OPERATOR")
        }.andExpect { status { isOk() } }
    }

    @Test
    fun `헬스 엔드포인트는 토큰 없이도 열려 있다`() {
        // 배포 도구·오케스트레이터가 토큰 없이 기동 여부를 봐야 한다(SecurityConfig 주석).
        // WebMvcTest에는 actuator가 없으므로 404(= 인증을 통과해 라우팅까지 갔다)여야 하고 401이면 안 된다.
        mockMvc.get("/actuator/health").andExpect { status { isNotFound() } }
    }

    @Test
    fun `역할이 맞으면 인가된다`() {
        // 토큰의 roles 클레임이 SecurityConfig의 변환기를 거쳐 ROLE_APPROVER 권한이 되어야 통과한다.
        mockMvc.get("/test-secure/approver-only") {
            header("Authorization", "Bearer APPROVER")
        }.andExpect { status { isOk() } }
    }

    @Test
    fun `역할이 다르면 403으로 막힌다`() {
        mockMvc.get("/test-secure/approver-only") {
            header("Authorization", "Bearer ANALYST")
        }.andExpect { status { isForbidden() } }
    }

    @Test
    fun `모르는 역할 문자열은 무시되고 요청 자체는 실패하지 않는다`() {
        // 토큰에 낯선 역할이 섞여도 인증은 통과해야 한다(OperationalRole.fromClaim이 null을 거른다).
        mockMvc.get("/test-secure/open") {
            header("Authorization", "Bearer UNKNOWN_ROLE.OPERATOR")
        }.andExpect { status { isOk() } }
    }

    @Test
    fun `모르는 역할만 있으면 인가는 거부된다`() {
        // 낯선 역할이 권한으로 둔갑하지 않는지 확인한다 — 인증은 되지만 APPROVER 권한은 없어야 한다.
        mockMvc.get("/test-secure/approver-only") {
            header("Authorization", "Bearer UNKNOWN_ROLE")
        }.andExpect { status { isForbidden() } }
    }
}

/** 역할 → Spring 권한 문자열 변환 규칙(프레임워크 없이 확인). */
class OperationalRoleTest {
    @Test
    fun `권한 문자열은 ROLE_ 접두사를 가진다`() {
        assertEquals("ROLE_APPROVER", OperationalRole.APPROVER.authority)
    }

    @Test
    fun `클레임 문자열을 대소문자 구분 없이 역할로 바꾼다`() {
        assertEquals(OperationalRole.OPERATOR, OperationalRole.fromClaim("operator"))
        assertEquals(OperationalRole.ADMIN, OperationalRole.fromClaim("ADMIN"))
    }

    @Test
    fun `모르는 값은 null이다`() {
        assertEquals(null, OperationalRole.fromClaim("superuser"))
    }
}
