package com.aeroops.c2

import com.aeroops.c2.audit.OperationalRole
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.core.convert.converter.Converter
import org.springframework.security.authentication.AbstractAuthenticationToken
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity
import org.springframework.security.core.GrantedAuthority
import org.springframework.security.core.authority.SimpleGrantedAuthority
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken
import org.springframework.security.web.SecurityFilterChain

/**
 * 인증·인가 설정. **기본값은 "아무 경로도 보호하지 않음"이다.**
 *
 * 왜 보호하지 않는가(가장 중요한 근거 — ADR 0006): legacy FastAPI에는 인증이 전혀 없다(identity 모듈은
 * 껍데기만 있고 8단계 예정). 전환의 핵심 전제는 "Kotlin이 legacy와 **같은 계약**을 낸다"이고(ADR 0004),
 * 그것을 Golden Replay(`tests/contracts/golden`)가 HTTP로 비교해 증명한다. Kotlin만 인증을 요구하면
 * 같은 시험을 돌릴 수 없어 전환 비교 자체가 불가능해진다. 그래서 **인프라는 만들어 두되 켜지 않는다.**
 *
 * 이 설계의 위험과 대비: "보안을 넣었다"고 착각하기 쉽다는 것이다. 그래서
 * ① 기본이 비보호임을 설정 이름(`aeroops.security.enabled`)과 이 주석에 드러내고,
 * ② 켰을 때 **실제로 막히는지**를 시험(`SecurityEnabledTest`)으로 증명하고,
 * ③ 끄면 통과하는 것도 시험(`SecurityDisabledTest`)해 두 상태를 모두 고정했다.
 *
 * 켜는 방법: `aeroops.security.enabled=true` + JWT 검증 설정
 * (`spring.security.oauth2.resourceserver.jwt.issuer-uri` 또는 `jwk-set-uri`). 실제 OIDC 공급자 연동은
 * 8단계(`docs/new_roadmap/08_통합검증_Cutover_Day14.md`)에서 한다.
 *
 * 연관 코드: 역할 정의는 [OperationalRole](audit 모듈), 오류 응답 형식은 [ApiErrorHandler],
 * 전환 전략은 ADR 0004, 이 결정 자체는 ADR 0006.
 */
@Configuration(proxyBeanMethods = false)
@EnableWebSecurity
class SecurityConfig {

    /**
     * 기본(전환 기간) 필터체인 — 모든 요청을 그대로 통과시킨다.
     *
     * CSRF를 끄는 이유: 이 서비스는 쿠키 세션이 아니라 토큰 기반 API다. 브라우저가 쿠키를 자동으로 실어
     * 보내는 상황이 없으므로 CSRF 토큰이 의미가 없고, 켜 두면 legacy에 없던 403이 생겨 계약이 깨진다.
     */
    @Bean
    @ConditionalOnProperty(name = ["aeroops.security.enabled"], havingValue = "false", matchIfMissing = true)
    fun permitAllFilterChain(http: HttpSecurity): SecurityFilterChain =
        http
            .csrf { it.disable() }
            .authorizeHttpRequests { it.anyRequest().permitAll() }
            .build()

    /**
     * 보안을 켰을 때의 필터체인 — 헬스 엔드포인트를 뺀 모든 요청에 유효한 JWT를 요구한다.
     *
     * 헬스를 여는 이유: 배포 도구(Go opsctl의 Health Gate, docs/planning/12)와 컨테이너 오케스트레이터가
     * 토큰 없이 기동 여부를 확인해야 한다. 헬스는 운용 데이터를 노출하지 않는다.
     */
    @Bean
    @ConditionalOnProperty(name = ["aeroops.security.enabled"], havingValue = "true")
    fun jwtFilterChain(http: HttpSecurity): SecurityFilterChain =
        http
            .csrf { it.disable() }
            .authorizeHttpRequests {
                it.requestMatchers("/actuator/health", "/actuator/health/**").permitAll()
                it.anyRequest().authenticated()
            }
            .oauth2ResourceServer { oauth2 -> oauth2.jwt { it.jwtAuthenticationConverter(jwtAuthenticationConverter()) } }
            .build()

    /**
     * JWT의 역할 클레임을 Spring 권한으로 바꾼다.
     *
     * 왜 기본 변환기를 쓰지 않나: Spring의 기본값은 OAuth2 `scope`/`scp` 클레임을 `SCOPE_*` 권한으로 바꾼다.
     * 우리 도메인 어휘는 scope가 아니라 **역할**(운영자·승인자·분석자·관리자)이고, 모르는 역할 문자열은
     * 조용히 무시해야 토큰에 낯선 값이 섞여도 요청 전체가 실패하지 않는다([OperationalRole.fromClaim]).
     */
    private fun jwtAuthenticationConverter(): Converter<Jwt, AbstractAuthenticationToken> =
        Converter { jwt ->
            val authorities: List<GrantedAuthority> = jwt.getClaimAsStringList(ROLES_CLAIM)
                .orEmpty()
                .mapNotNull { OperationalRole.fromClaim(it) }
                .map { SimpleGrantedAuthority(it.authority) }
            // 이름(principal)을 직접 넘기지 않는다 — JWT의 subject가 없을 수도 있어서, Spring이 가진
            // 기본 규칙(subject 우선)에 맡기는 편이 안전하다.
            JwtAuthenticationToken(jwt, authorities)
        }

    private companion object {
        /** 역할이 담기는 JWT 클레임 이름. 실제 OIDC 공급자를 붙일 때 그쪽 클레임 이름과 맞춰야 한다(8단계). */
        const val ROLES_CLAIM = "roles"
    }
}

/**
 * 메서드 단위 권한 검사(`@PreAuthorize` 등)를 **보안을 켰을 때만** 활성화한다.
 *
 * 왜 [SecurityConfig]와 분리했나: `@EnableMethodSecurity`를 항상 켜 두면, 보안이 꺼진 전환 기간에도
 * `@PreAuthorize`가 붙은 메서드가 인증 없는 요청을 거부한다. 그러면 "기본은 비보호"라는 전제(ADR 0006)가
 * 조용히 깨져 Golden Replay 비교가 실패한다. 그래서 필터체인과 같은 스위치(`aeroops.security.enabled`)로
 * 함께 켜지도록 별도 설정으로 뺐다.
 *
 * 연관 코드: [SecurityConfig], 두 상태를 각각 고정한 시험은 `SecurityDisabledTest`·`SecurityEnabledTest`.
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(name = ["aeroops.security.enabled"], havingValue = "true")
@EnableMethodSecurity
class MethodSecurityConfig
