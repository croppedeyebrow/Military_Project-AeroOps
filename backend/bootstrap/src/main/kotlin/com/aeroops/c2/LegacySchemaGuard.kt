package com.aeroops.c2

import java.sql.Connection
import javax.sql.DataSource

/**
 * "비어 있지 않은 DB를 Flyway baseline으로 받아들여도 되는가"를 판단하는 안전장치.
 *
 * 왜 필요한가(근거): `spring.flyway.baseline-on-migrate=true`는 "테이블이 이미 있는 DB는 V1(전체 스키마 생성)이
 * 이미 적용된 것으로 치고 건너뛴다"는 뜻이다. 이 설정은 이미 Alembic 0005까지 적용된 legacy DB를 위한 것인데,
 * 설정 실수로 **엉뚱한 DB**(다른 서비스의 DB, Alembic 0004 이전 상태의 DB 등)를 가리켜도 Flyway는 아무
 * 검사 없이 baseline 처리해버린다. 그러면 우리 테이블이 하나도 없는데 "마이그레이션 성공"으로 보이고, 이후
 * 기동·질의에서 뒤늦게 터진다. 그래서 baseline이 일어나기 직전에 DB가 정말 "Alembic 0005 상태"인지 확인한다.
 *
 * 규칙(순서대로):
 * 1. `flyway_schema_history`가 이미 있다 → Flyway가 관리 중인 DB라 baseline이 일어나지 않는다. 통과.
 * 2. 업무 테이블이 하나도 없다(빈 DB) → Flyway가 V1을 실제로 실행한다. 통과.
 * 3. 그 외(테이블은 있는데 Flyway 이력이 없음) → legacy DB여야 한다. `alembic_version`이 정확히
 *    [EXPECTED_ALEMBIC_HEAD]일 때만 통과하고, 아니면 이유를 적어 기동을 실패시킨다.
 *
 * 연관 코드:
 * - 호출 지점: [FlywayMigrationConfig] (마이그레이션 직전에 실행).
 * - baseline 대상 스키마: `db/migration/V1__baseline_from_alembic_0005.sql` (헤더에 두 경로 설명).
 * - 시험: `LegacySchemaGuardTest`(규칙 3가지 + 통과 경로), `LegacyDatabaseMigrationTest`(실제 기존 DB 스냅샷).
 * - 배경: ADR 0004 "스키마 소유를 Kotlin(Flyway)으로 변경", Alembic 동결 지점 = 0005.
 *
 * `spatial_ref_sys`를 업무 테이블에서 뺀 이유: PostGIS 확장이 모든 DB에 만드는 시스템 테이블이라, 이것만
 * 있는 "사실상 빈 DB"를 기존 DB로 오인하면 안 된다.
 */
class LegacySchemaGuard(private val dataSource: DataSource) {

    /** baseline이 허용되지 않으면 [IllegalStateException]을 던진다(Spring이 기동을 중단시킨다). */
    fun verifyBaselineAllowed() {
        dataSource.connection.use { connection ->
            if (tableExists(connection, FLYWAY_HISTORY_TABLE)) return

            val businessTables = businessTables(connection)
            if (businessTables.isEmpty()) return

            val alembicVersion = alembicVersion(connection)
            check(alembicVersion == EXPECTED_ALEMBIC_HEAD) {
                "Flyway baseline을 거부한다: DB에 테이블이 있고 Flyway 이력이 없는데 " +
                    "Alembic 버전이 '$alembicVersion'이다(기대값 '$EXPECTED_ALEMBIC_HEAD'). " +
                    "접속 대상 DB가 맞는지, legacy를 Alembic 0005까지 올렸는지 확인하라. " +
                    "발견한 테이블: ${businessTables.sorted()}"
            }
        }
    }

    private fun tableExists(connection: Connection, name: String): Boolean =
        connection.prepareStatement("select to_regclass(?) is not null").use { statement ->
            statement.setString(1, name)
            statement.executeQuery().use { it.next() && it.getBoolean(1) }
        }

    private fun businessTables(connection: Connection): List<String> =
        connection.createStatement().use { statement ->
            statement.executeQuery(
                """
                select table_name from information_schema.tables
                where table_schema = current_schema()
                  and table_type = 'BASE TABLE'
                  and table_name <> 'spatial_ref_sys'
                """.trimIndent(),
            ).use { rows -> buildList { while (rows.next()) add(rows.getString(1)) } }
        }

    /** alembic_version 테이블이 없거나 비어 있으면 null. Alembic은 항상 정확히 한 행을 둔다. */
    private fun alembicVersion(connection: Connection): String? {
        if (!tableExists(connection, "alembic_version")) return null
        return connection.createStatement().use { statement ->
            statement.executeQuery("select version_num from alembic_version").use { rows ->
                if (rows.next()) rows.getString(1) else null
            }
        }
    }

    companion object {
        /** Alembic이 동결된 마지막 리비전. ADR 0004 / V1 baseline과 같은 지점이어야 한다. */
        const val EXPECTED_ALEMBIC_HEAD = "0005"
        private const val FLYWAY_HISTORY_TABLE = "flyway_schema_history"
    }
}
