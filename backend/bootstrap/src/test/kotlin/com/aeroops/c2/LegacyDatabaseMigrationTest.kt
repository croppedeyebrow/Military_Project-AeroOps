package com.aeroops.c2

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.jdbc.core.JdbcTemplate
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * 마이그레이션 게이트 ② — **Alembic 0005까지 적용된 기존 DB**(실제 앱이 만든 데이터 포함)에서 앱이 기동되고,
 * Flyway가 V1을 **다시 실행하지 않고** baseline으로만 기록한다. 데이터는 그대로 남는다.
 *
 * 기존 DB를 만드는 방법: 컨테이너가 뜬 직후 `legacy-alembic-0005-snapshot.sql`을 실행한다(`withScript`).
 * 이 파일은 Alembic을 실제로 돌린 DB에 legacy 앱을 띄워 만든 덤프다(파일 헤더에 생성 방법 기록).
 *
 * 이 시험이 증명하는 것:
 * - 앱이 기동된다(= `LegacySchemaGuard`가 Alembic 0005를 확인하고 baseline을 허용했다).
 * - Flyway 이력이 BASELINE 1행뿐이다 — V1이 실행됐다면 "relation already exists"로 실패했을 것이다.
 * - 기존 행(기체·텔레메트리·명령·이벤트·감사·배포 기록)과 지오메트리가 그대로 읽힌다(데이터 보존, REQ: 기존 데이터 일괄
 *   폐기 금지 — docs/planning/11 §5).
 * - `alembic_version`이 그대로 남는다(legacy가 이 DB를 계속 쓰는 전환 기간에 필요 — ADR 0004).
 *
 * 연관 코드: `LegacySchemaGuard`, `FlywayMigrationConfig`, 반대 경로 시험 `FreshDatabaseMigrationTest`.
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest
class LegacyDatabaseMigrationTest(@Autowired private val jdbc: JdbcTemplate) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.withScript(PostgisContainers.LEGACY_SNAPSHOT)
    }

    private fun count(table: String): Int =
        jdbc.queryForObject("select count(*) from $table", Int::class.java)!!

    @Test
    fun `Flyway 이력에는 BASELINE 한 행만 있고 V1은 다시 실행되지 않는다`() {
        val rows = jdbc.queryForList(
            "select version, type, success from flyway_schema_history order by installed_rank",
        )
        assertEquals(1, rows.size, "이력 행: $rows")
        assertEquals("1", rows[0]["version"])
        assertEquals("BASELINE", rows[0]["type"])
        assertEquals(true, rows[0]["success"])
    }

    @Test
    fun `기존 데이터가 전부 보존된다`() {
        // 스냅샷을 만들 때 실제 앱이 쌓은 건수(snapshot 파일 헤더 참고)
        val expected = mapOf(
            "assets" to 1, "telemetry_frames" to 3, "asset_latest_state" to 1, "commands" to 1,
            "command_events" to 3, "event_log" to 6, "audit_logs" to 2, "deployments" to 1,
            "operation_sessions" to 1,
        )
        assertEquals(expected, expected.keys.associateWith { count(it) })
    }

    @Test
    fun `PostGIS 지오메트리 값이 baseline 이후에도 읽힌다`() {
        val wkt = jdbc.queryForObject(
            "select ST_AsText(position) from telemetry_frames order by sequence_no limit 1",
            String::class.java,
        )
        assertNotNull(wkt)
        assertTrue(wkt.startsWith("POINT Z"), wkt) // 3D 점(경도·위도·고도)이 그대로다
    }

    @Test
    fun `alembic_version은 그대로 남아 legacy가 계속 쓸 수 있다`() {
        assertEquals("0005", jdbc.queryForObject("select version_num from alembic_version", String::class.java))
    }
}
