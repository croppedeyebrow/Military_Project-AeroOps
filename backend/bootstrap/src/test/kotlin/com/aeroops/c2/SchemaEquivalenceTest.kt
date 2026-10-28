package com.aeroops.c2

import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.DriverManager
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * 마이그레이션 게이트 ③ — **V1이 만든 스키마 == Alembic이 만든 스키마**.
 *
 * 왜 필요한가(근거): `FreshDatabaseMigrationTest`(빈 DB)와 `LegacyDatabaseMigrationTest`(기존 DB)는 각각
 * "성공한다"만 보여준다. 정작 중요한 건 두 경로가 **같은 스키마**에 도달하는가다. V1이 Alembic 결과와
 * 조금이라도 다르면(누락된 인덱스, 다른 기본값, 다른 SRID…) 새로 만든 DB와 기존 DB가 서로 다른 시스템이 되고, Kotlin이
 * 새 DB에서 통과한 시험이 운영 DB에서는 틀릴 수 있다.
 *
 * 비교 방법: 두 컨테이너를 만든다.
 * - A: 빈 DB에 **V1 파일만** 실행한 상태(Flyway가 빈 DB에서 하는 일과 같다)
 * - B: Alembic 0005 스냅샷을 복원한 상태(기존 DB 경로)
 * 둘의 컬럼·인덱스·제약·시퀀스·지오메트리 등록을 정규화한 목록으로 뽑아 같은지 본다. Alembic·Flyway 전용
 * 메타 테이블(`alembic_version`, `flyway_schema_history`)과 PostGIS 시스템 테이블(`spatial_ref_sys`)은 제외한다.
 *
 * 연관 코드: V1 `db/migration/V1__baseline_from_alembic_0005.sql`, 스냅샷 `db/legacy-alembic-0005-snapshot.sql`,
 * 컨테이너 생성 `PostgisContainers`.
 */
@Testcontainers(disabledWithoutDocker = true)
class SchemaEquivalenceTest {
    companion object {
        @Container
        @JvmStatic
        val fromBaseline: PostgreSQLContainer = PostgisContainers.withScript(PostgisContainers.V1_BASELINE)

        @Container
        @JvmStatic
        val fromAlembic: PostgreSQLContainer = PostgisContainers.withScript(PostgisContainers.LEGACY_SNAPSHOT)

        private val EXCLUDED = "('alembic_version','flyway_schema_history','spatial_ref_sys')"
    }

    /** 스키마를 사람이 읽을 수 있는 정규화된 줄 목록으로 만든다. 순서에 의존하지 않도록 정렬한다. */
    private fun fingerprint(container: PostgreSQLContainer): Map<String, List<String>> =
        DriverManager.getConnection(container.jdbcUrl, container.username, container.password).use { c ->
            fun lines(sql: String): List<String> = c.createStatement().use { st ->
                st.executeQuery(sql).use { rs -> buildList { while (rs.next()) add(rs.getString(1)) } }.sorted()
            }
            mapOf(
                "columns" to lines(
                    """
                    select table_name || '.' || column_name || ' type=' || udt_name ||
                           ' null=' || is_nullable || ' default=' || coalesce(column_default, '') ||
                           ' len=' || coalesce(character_maximum_length::text, '') ||
                           ' prec=' || coalesce(numeric_precision::text, '')
                    from information_schema.columns
                    where table_schema = 'public' and table_name not in $EXCLUDED
                    """.trimIndent(),
                ),
                "indexes" to lines(
                    "select tablename || ' ' || indexdef from pg_indexes " +
                        "where schemaname = 'public' and tablename not in $EXCLUDED",
                ),
                "constraints" to lines(
                    "select conrelid::regclass::text || ' ' || conname || ' ' || pg_get_constraintdef(oid) " +
                        "from pg_constraint where connamespace = 'public'::regnamespace " +
                        "and conrelid::regclass::text not in ('alembic_version','flyway_schema_history')",
                ),
                "sequences" to lines(
                    "select sequencename || ' ' || data_type || ' ' || start_value || ' ' || increment_by " +
                        "from pg_sequences where schemaname = 'public'",
                ),
                "geometry" to lines(
                    "select f_table_name || '.' || f_geometry_column || ' srid=' || srid || ' type=' || type || " +
                        "' dim=' || coord_dimension from geometry_columns where f_table_schema = 'public'",
                ),
            )
        }

    @Test
    fun `V1이 만든 스키마와 Alembic이 만든 스키마는 같다`() {
        val baseline = fingerprint(fromBaseline)
        val alembic = fingerprint(fromAlembic)

        // 빈 집합끼리 같다고 통과하지 않도록 최소한의 크기를 확인한다(컬럼 100개 이상, 인덱스 10개 이상 등).
        assertTrue(baseline.getValue("columns").size > 100, "컬럼 수가 비정상적으로 적다: ${baseline["columns"]?.size}")
        assertTrue(baseline.getValue("indexes").size >= 10)
        assertEquals(4, baseline.getValue("geometry").size)

        baseline.forEach { (kind, expected) ->
            assertEquals(
                expected,
                alembic.getValue(kind),
                "[$kind] 두 경로의 스키마가 다르다 — V1이 Alembic 0005와 어긋났다",
            )
        }
    }
}
