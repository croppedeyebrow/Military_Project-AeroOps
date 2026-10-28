package com.aeroops.c2

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.health.actuate.endpoint.HealthEndpoint
import org.springframework.boot.health.contributor.Status
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.jdbc.core.JdbcTemplate
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * 마이그레이션 게이트 ① — **빈 DB**에서 앱이 기동되고 Flyway가 V1을 실제로 실행한다.
 *
 * 왜 `@SpringBootTest`인가: Flyway 설정(`application.yml`의 baseline-on-migrate 등)·`FlywayMigrationConfig`·
 * `LegacySchemaGuard`·JPA(`ddl-auto=validate`)가 **실제 앱과 같은 경로**로 동작하는지 봐야 한다. Flyway를
 * 시험 안에서 따로 설정하면 yml과 어긋나도 시험은 통과하는 문제가 생긴다.
 *
 * 이 시험이 증명하는 것:
 * - 앱 컨텍스트가 뜨고 헬스가 UP이다(DB 연결 포함) — 구 AeroOpsC2ApplicationTest의 역할을 흡수했다.
 * - 이력에 V1이 SQL로 성공 기록되어 있다(baseline이 아니라 실제 실행).
 * - Alembic이 만들던 14개 업무 테이블과 4개 지오메트리 컬럼이 존재하고, Alembic 전용 테이블은 없다.
 *
 * 연관 코드: V1 마이그레이션 `db/migration/V1__baseline_from_alembic_0005.sql`, 반대 경로 시험은
 * `LegacyDatabaseMigrationTest`, 두 경로의 스키마가 같은지는 `SchemaEquivalenceTest`.
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest
class FreshDatabaseMigrationTest(
    @Autowired private val jdbc: JdbcTemplate,
    @Autowired private val health: HealthEndpoint,
) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.empty()

        /** legacy(Alembic 0001~0005)가 만들던 업무 테이블 14개 — docs/planning/13 §2 Context Map의 소유 테이블 전체. */
        val BUSINESS_TABLES = setOf(
            "alerts", "asset_latest_state", "assets", "audit_logs", "command_events", "commands",
            "deployments", "event_log", "geofences", "mission_routes", "missions",
            "operation_sessions", "sync_sessions", "telemetry_frames",
        )
    }

    @Test
    fun `컨텍스트가 기동되고 DB를 포함한 헬스가 UP이다`() {
        assertEquals(Status.UP, health.health().status)
    }

    @Test
    fun `Flyway 이력에 V1이 실제 SQL 실행으로 성공 기록된다`() {
        val rows = jdbc.queryForList(
            "select version, type, script, success from flyway_schema_history order by installed_rank",
        )
        assertEquals(1, rows.size, "이력 행: $rows")
        assertEquals("1", rows[0]["version"])
        assertEquals("SQL", rows[0]["type"]) // BASELINE이면 V1이 실행되지 않고 건너뛴 것이다
        assertEquals("V1__baseline_from_alembic_0005.sql", rows[0]["script"])
        assertEquals(true, rows[0]["success"])
    }

    @Test
    fun `업무 테이블 14개가 모두 만들어지고 Alembic 전용 테이블은 없다`() {
        val tables = jdbc.queryForList(
            "select table_name from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE'",
            String::class.java,
        ).toSet()
        assertTrue(tables.containsAll(BUSINESS_TABLES), "누락: ${BUSINESS_TABLES - tables}")
        assertTrue("alembic_version" !in tables, "Alembic 전용 테이블이 새 DB에 있으면 안 된다")
    }

    @Test
    fun `PostGIS 지오메트리 컬럼 4개가 등록된다`() {
        val geometry = jdbc.queryForList(
            "select f_table_name || '.' || f_geometry_column from geometry_columns where f_table_schema = 'public'",
            String::class.java,
        ).toSet()
        assertEquals(
            setOf(
                "telemetry_frames.position", "asset_latest_state.position",
                "geofences.geom", "mission_routes.route",
            ),
            geometry,
        )
    }
}
