package com.aeroops.c2

import org.springframework.jdbc.datasource.DriverManagerDataSource
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.DriverManager
import kotlin.test.Test
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/**
 * `LegacySchemaGuard`의 규칙을 하나씩 검증한다(통과해야 할 때 통과, 막아야 할 때 막는지).
 *
 * 왜 Spring 없이 하나: 안전장치는 "엉뚱한 DB를 baseline하지 않는다"가 핵심이라, 다양한 DB 상태(빈 DB,
 * 다른 서비스 DB, Alembic 0004 …)를 빠르게 만들어 봐야 한다. 상태마다 앱을 띄우면 느리고 상태 구성도 어렵다.
 * 대신 컨테이너 하나 안에 상태별 **스키마(schema)** 를 따로 만들고, 접속 URL의 `currentSchema`로 가리킨다
 * (Guard가 `current_schema()` 기준으로 검사하기 때문에 실제 DB를 따로 만든 것과 같다).
 *
 * 연관 코드: `LegacySchemaGuard`(규칙 정의), `FlywayMigrationConfig`(호출 지점),
 * 실제 기존 DB 스냅샷으로 앱을 띄워 통과를 확인하는 시험은 `LegacyDatabaseMigrationTest`.
 */
@Testcontainers(disabledWithoutDocker = true)
class LegacySchemaGuardTest {
    companion object {
        @Container
        @JvmStatic
        val database: PostgreSQLContainer = PostgisContainers.empty()
    }

    /** [setupSql]로 만든 이름 붙은 스키마를 가리키는 DataSource로 Guard를 만든다. */
    private fun guardFor(schema: String, setupSql: List<String> = emptyList()): LegacySchemaGuard {
        DriverManager.getConnection(database.jdbcUrl, database.username, database.password).use { c ->
            c.createStatement().use { st ->
                st.execute("create schema if not exists $schema")
                setupSql.forEach { st.execute("set search_path to $schema; $it") }
            }
        }
        val dataSource = DriverManagerDataSource(
            "${database.jdbcUrl}${if ("?" in database.jdbcUrl) "&" else "?"}currentSchema=$schema",
            database.username,
            database.password,
        )
        return LegacySchemaGuard(dataSource)
    }

    @Test
    fun `빈 DB는 통과한다(Flyway가 V1을 실제로 실행할 것이다)`() {
        guardFor("guard_empty").verifyBaselineAllowed()
    }

    @Test
    fun `Alembic 0005 상태의 기존 DB는 통과한다(baseline 허용)`() {
        guardFor(
            "guard_legacy_ok",
            listOf(
                "create table alembic_version (version_num varchar(32) not null)",
                "insert into alembic_version values ('0005')",
                "create table assets (id text primary key)",
            ),
        ).verifyBaselineAllowed()
    }

    @Test
    fun `Flyway가 이미 관리 중인 DB는 다른 테이블이 있어도 통과한다`() {
        guardFor(
            "guard_flyway_managed",
            listOf("create table flyway_schema_history (installed_rank int)", "create table anything (id int)"),
        ).verifyBaselineAllowed()
    }

    @Test
    fun `Alembic 버전이 0005가 아니면 거부한다`() {
        val guard = guardFor(
            "guard_old_alembic",
            listOf(
                "create table alembic_version (version_num varchar(32) not null)",
                "insert into alembic_version values ('0004')",
                "create table assets (id text primary key)",
            ),
        )
        val error = assertFailsWith<IllegalStateException> { guard.verifyBaselineAllowed() }
        assertTrue("0004" in error.message!! && "0005" in error.message!!, error.message)
    }

    @Test
    fun `우리와 무관한 테이블만 있는 DB는 거부한다(엉뚱한 DB를 baseline하지 않는다)`() {
        val guard = guardFor("guard_foreign_db", listOf("create table orders (id int)", "create table customers (id int)"))
        val error = assertFailsWith<IllegalStateException> { guard.verifyBaselineAllowed() }
        // 어떤 테이블 때문에 거부했는지 메시지에 나와야 원인을 찾을 수 있다
        assertTrue("orders" in error.message!!, error.message)
    }

    @Test
    fun `PostGIS 시스템 테이블만 있는 사실상 빈 DB는 통과한다`() {
        // public 스키마에는 PostGIS가 spatial_ref_sys를 만든다. 이것을 "기존 DB"로 오인하면 안 된다.
        val dataSource = DriverManagerDataSource(
            "${database.jdbcUrl}${if ("?" in database.jdbcUrl) "&" else "?"}currentSchema=public",
            database.username,
            database.password,
        )
        LegacySchemaGuard(dataSource).verifyBaselineAllowed()
    }
}
