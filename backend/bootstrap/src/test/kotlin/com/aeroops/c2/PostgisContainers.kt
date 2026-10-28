package com.aeroops.c2

import org.testcontainers.postgresql.PostgreSQLContainer
import org.testcontainers.utility.DockerImageName

/**
 * DB 시험이 공통으로 쓰는 PostGIS 컨테이너 생성기.
 *
 * 왜 한 곳인가: 이미지 태그를 시험마다 복붙하면 한쪽만 올라가 "어떤 시험은 다른 PostGIS 버전에서 돈다"는
 * 불일치가 생긴다. 이미지는 운영 후보와 같은 `postgis/postgis:16-3.4-alpine`(infra/docker-compose.yml의
 * postgres 서비스와 동일)이다.
 *
 * 왜 `asCompatibleSubstituteFor("postgres")`: Testcontainers는 이미지를 공식 `postgres`의 호환 이미지로
 * 선언해야 PostgreSQL 컨테이너로 다룬다(PostGIS 이미지는 공식 postgres 이미지 기반이다).
 *
 * 연관 코드: 이 헬퍼를 쓰는 시험 — FreshDatabaseMigrationTest, LegacyDatabaseMigrationTest,
 * SchemaEquivalenceTest, LegacySchemaGuardTest. 스키마 파일은 아래 상수가 가리키는 두 개다.
 */
object PostgisContainers {
    private val IMAGE: DockerImageName =
        DockerImageName.parse("postgis/postgis:16-3.4-alpine").asCompatibleSubstituteFor("postgres")

    /** Flyway가 빈 DB에서 실행하는 baseline(main 리소스). */
    const val V1_BASELINE = "db/migration/V1__baseline_from_alembic_0005.sql"

    /** "Alembic 0005까지 적용된 기존 DB + 실제 앱이 만든 데이터" 스냅샷(test 리소스). */
    const val LEGACY_SNAPSHOT = "db/legacy-alembic-0005-snapshot.sql"

    /** 아무 것도 없는 새 DB. */
    fun empty(): PostgreSQLContainer = PostgreSQLContainer(IMAGE)

    /** 컨테이너가 뜬 직후 [classpathScript]를 실행해 특정 상태의 DB를 만든다(기존 DB 재현에 사용). */
    fun withScript(classpathScript: String): PostgreSQLContainer =
        PostgreSQLContainer(IMAGE).withInitScript(classpathScript)
}
