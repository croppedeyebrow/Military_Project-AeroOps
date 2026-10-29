package com.aeroops.c2

import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.web.server.LocalServerPort
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * 관측성 설정이 실제로 **외부에서 읽을 수 있는 형태로** 노출되는지 확인한다.
 *
 * 왜 필요한가(근거): 7단계에서 legacy에 Prometheus 메트릭과 Grafana 대시보드를 붙였다
 * (`infra/grafana/provisioning/dashboards/aeroops-overview.json`). 전환 기간에는 legacy와 Kotlin이 **같은
 * Prometheus로 동시에** 수집되므로, Kotlin 쪽도 같은 방식으로 긁을 수 있어야 "전환 전후 수치"를 비교할 수 있다.
 * 설정 파일만 보고 "되겠지" 하고 넘어가면, 정작 수집 경로가 404여도 모른다.
 *
 * 왜 `webEnvironment = RANDOM_PORT`인가: Actuator 엔드포인트는 실제 HTTP 서버에 붙는다. MockMvc 슬라이스로는
 * 노출 설정(`management.endpoints.web.exposure`)이 그대로 적용되지 않아 의미가 없다.
 *
 * 연관 코드: 설정은 `application.yml`의 `management`·`logging`, 수집 설정은 `infra/prometheus/prometheus.yml`,
 * legacy 쪽 대응은 `legacy-backend/app/core/metrics.py`(같은 Prometheus 형식).
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ObservabilityTest(@LocalServerPort private val port: Int) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.empty()
    }

    /**
     * 표준 HTTP 클라이언트로 실제 포트를 호출한다.
     *
     * 왜 Spring의 시험용 클라이언트를 안 쓰나: Boot 4에는 `TestRestTemplate`이 없다(실제로 확인). 표준
     * `java.net.http.HttpClient`면 의존성 없이 "밖에서 긁는" 상황을 그대로 재현할 수 있다 — Prometheus가
     * 이 경로를 HTTP로 긁는다는 점에서 오히려 실제와 가깝다.
     */
    private val http: HttpClient = HttpClient.newHttpClient()

    private fun get(path: String): HttpResponse<String> = http.send(
        HttpRequest.newBuilder(URI("http://localhost:$port$path")).GET().build(),
        HttpResponse.BodyHandlers.ofString(),
    )

    @Test
    fun `Prometheus 수집 경로가 메트릭을 내보낸다`() {
        val response = get("/actuator/prometheus")

        assertEquals(200, response.statusCode(), "Prometheus 수집 경로가 열려 있지 않다")
        val body = response.body()
        // Prometheus 텍스트 형식인지(주석 메타데이터 + 샘플) 최소한으로 확인한다.
        assertTrue(body.contains("# HELP"), "Prometheus 텍스트 형식이 아니다")
        assertTrue(body.contains("jvm_memory_used_bytes"), "기본 JVM 메트릭이 없다")
    }

    @Test
    fun `메트릭에 구현을 구분하는 application 태그가 붙는다`() {
        // 전환 기간에는 legacy와 Kotlin 수치가 같은 Prometheus에 섞인다. 이 태그가 없으면 대시보드에서
        // 어느 구현의 값인지 구분할 수 없다.
        val body = get("/actuator/prometheus").body()
        assertTrue(
            body.contains("""application="aeroops-c2-core""""),
            "application 태그가 메트릭에 없다",
        )
    }

    @Test
    fun `HTTP 요청 메트릭이 수집된다`() {
        // 먼저 아무 요청이나 보내 메트릭이 생기게 한다.
        get("/actuator/health")

        val body = get("/actuator/prometheus").body()
        assertTrue(
            body.contains("http_server_requests_seconds"),
            "HTTP 요청 지연 메트릭이 없다 — 전환 전후 성능 비교의 기본 지표다",
        )
    }

    @Test
    fun `헬스 엔드포인트가 DB 상태를 포함해 UP을 보고한다`() {
        val response = get("/actuator/health")

        assertEquals(200, response.statusCode())
        assertTrue(response.body().contains("\"status\":\"UP\""), response.body())
    }

    @Test
    fun `liveness와 readiness를 따로 조회할 수 있다`() {
        // 배포 도구·오케스트레이터가 "살아 있음"과 "트래픽 받을 준비됨"을 구분해서 봐야 한다
        // (docs/planning/12의 Go opsctl Health Gate).
        assertEquals(200, get("/actuator/health/liveness").statusCode())
        assertEquals(200, get("/actuator/health/readiness").statusCode())
    }
}
