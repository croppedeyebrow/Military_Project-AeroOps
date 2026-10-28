# backend — Kotlin·Spring Boot C2 Core

FastAPI(`../legacy-backend/`)를 점진적으로 대체하는 지휘통제(C2) 코어다(ADR 0004). 구조·원칙은
`docs/planning/02_백엔드_아키텍처.md`, 전환 계획은 `docs/new_roadmap/`을 따른다.

## 현재 상태 (2단계 진행 중)

| 모듈 | 컨텍스트 | 의존해도 되는 모듈 | 상태 |
|---|---|---|---|
| `shared-kernel` | (공유) ID·값 객체(`AssetId`, `BootId`). 프레임워크 비의존 순수 Kotlin | — | 완료 |
| `mission` | Mission Operations | 없음 | 모듈 선언만(2-2) |
| `operational-picture` | Operational Picture | 없음 | 선언 + `domain/ObservationKey` |
| `safety-policy` | Safety & Policy | 없음 | 모듈 선언만 |
| `audit` | Identity & Audit(감사) | 없음 | 모듈 선언만 |
| `command-control` | Command & Control | mission, safety-policy, operational-picture, audit | 모듈 선언만 |
| `incident` | Incident Management | operational-picture, safety-policy, mission, audit | 모듈 선언만 |
| `bootstrap` | Spring Boot 진입점·조립·**구조 검증 시험** | 전부 | 기동·검증 완료 |

의존 방향의 근거는 `docs/planning/10 §4`(Context Map)와 `docs/planning/13 §2`이다. 상류(mission·
operational-picture·safety-policy·audit)는 다른 컨텍스트를 모르고, 하류(command-control·incident)만 상류를
안다. `command-control`과 `incident`는 서로를 모른다(경보는 명령 처리와 독립이어야 하므로).

영속성(JPA·PostGIS·Flyway)은 2-3에서 연결했다(아래 "DB와 마이그레이션"). 보안(OIDC/JWT)·Outbox·관측성·CI는
후속 유닛에서 추가한다.

## 모듈 내부 구조

각 컨텍스트 모듈은 다음 패키지로 나눈다. 의존 방향은 **adapter → application → domain** 한 방향이다.

```
com.aeroops.c2.<context>/        ← 모듈 기본 패키지 = 다른 모듈에 공개하는 API(포트·이벤트·ID)
├─ domain/                       순수 Kotlin 규칙. Spring·JPA·Jackson을 모른다
├─ application/                  유스케이스·트랜잭션. 포트(인터페이스)를 정의한다
└─ adapter/
   ├─ inbound/                   REST·WebSocket·Redis 수신 (컨트롤러 등)
   └─ outbound/                  JPA·Redis 발행·외부 호출 (포트 구현)
```

설계 문서의 `adapter-in`/`adapter-out`은 `in`이 Kotlin 예약어이고 하이픈이 패키지명에 못 쓰여서
`adapter.inbound`/`adapter.outbound`로 구현한다. 하위 패키지(`domain` 등)는 모듈 **내부**라서 다른 모듈이
접근하면 검증이 실패한다. 빈 패키지는 git에 남지 않으므로 레이어 패키지는 첫 클래스가 생길 때 만든다.

## 구조 규칙은 어떻게 강제되나 (3겹)

| 겹 | 막는 것 | 어디서 |
|---|---|---|
| 1. Gradle 의존성 | 선언하지 않은 모듈의 클래스를 아예 컴파일할 수 없다 | 각 `<module>/build.gradle.kts` |
| 2. Spring Modulith | 모듈 간 순환, 다른 모듈의 내부 패키지 접근, `allowedDependencies`에 없는 의존 | `bootstrap` `ModularityTest` |
| 3. ArchUnit | 모듈 안의 레이어: domain이 프레임워크를 앎, application이 adapter 구현을 앎, inbound↔outbound 직접 호출 | `bootstrap` `LayeringRulesTest`, 규칙 정의 `LayeringRules` |

"규칙이 있다"가 아니라 "규칙이 작동한다"를 보이려고, 위반 샘플(`bootstrap/src/test/.../archfixture`)에서
검사가 실패하고 정상 대조군에서 통과하는 것까지 시험한다. 실제 모듈 코드에서도 직접 확인했다 — domain에
Spring 어노테이션을 붙이면 `LayeringRulesTest`가, incident가 command-control을 import하면 컴파일이 막힌다.

## DB와 마이그레이션 (Flyway)

**스키마 변경은 Flyway만 한다**(ADR 0004). legacy의 Alembic은 `0005`에서 동결됐다.

| 상황 | 동작 |
|---|---|
| 빈 DB | Flyway가 `V1__baseline_from_alembic_0005.sql`을 **실행**해 전체 스키마(14 테이블, PostGIS 지오메트리 4개)를 만든다 |
| 기존 DB(Alembic 0005까지 적용) | V1을 **건너뛰고** baseline으로만 기록한다. 기존 데이터·`alembic_version`은 그대로 |
| 엉뚱한 DB(Alembic 0005가 아님) | `LegacySchemaGuard`가 기동을 **거부**한다(baseline해서 테이블 없이 "성공"하는 것을 막는다) |

접속 정보는 환경변수로 바꾼다: `C2_DB_URL`(기본 `jdbc:postgresql://localhost:5433/aeroops`), `C2_DB_USER`,
`C2_DB_PASSWORD`. 기본값은 로컬 dev 스택(`infra/docker-compose.yml`)이다. **주의**: 그 DB는 legacy FastAPI와 같은
DB라서 Kotlin이 처음 접속하면 `flyway_schema_history` 테이블이 생기고 baseline으로 등록된다(데이터는 건드리지 않음).

실제 dev DB 복사본(텔레메트리 33,121행 규모)으로 리허설을 마쳤다 — baseline 기록만 하고 데이터·`alembic_version`은
그대로였고, **그 뒤에도 legacy FastAPI가 같은 DB에서 정상 동작**(alembic head 인식, 읽기·쓰기, 두 앱 동시 기동)했다.
자세한 결과는 `docs/dev_history/new_history/02_Kotlin_Spring기반_Day02-03.md`.

새 마이그레이션을 추가할 때의 규칙:
1. `src/main/resources/db/migration/V<번호>__<컨텍스트>_<설명>.sql`. 번호는 전체에서 유일하게 증가시킨다.
2. **이미 적용된 파일은 절대 수정하지 않는다**(Flyway가 체크섬을 검증한다). 특히 V1은 건드리지 않는다.
3. legacy가 쓰는 테이블은 **Expand 전용**(컬럼 추가, 새 테이블)만 한다. 제약 교체·컬럼 삭제는 그 컨텍스트의 쓰기
   주체가 Kotlin으로 넘어간 뒤에만 한다(예: `boot_id` 유일 제약 교체 — ADR 0005 "적용 시점 제약").
4. 엔티티를 만들면 `ddl-auto=validate`가 엔티티와 스키마의 불일치를 기동 시점에 잡아준다.

**마이그레이션 게이트 시험**(실제 PostGIS 컨테이너, Docker 필요 — 없으면 건너뛰므로 CI에는 Docker가 있어야 한다):

| 시험 | 증명하는 것 |
|---|---|
| `FreshDatabaseMigrationTest` | 빈 DB에서 앱 기동, V1이 SQL로 실행됨, 14 테이블·지오메트리 4개 |
| `LegacyDatabaseMigrationTest` | 기존 DB 스냅샷(실제 앱 데이터 포함)에서 baseline만 기록, 데이터·`alembic_version` 보존 |
| `SchemaEquivalenceTest` | V1이 만든 스키마 == Alembic이 만든 스키마(컬럼·인덱스·제약·시퀀스·지오메트리) |
| `LegacySchemaGuardTest` | 안전장치 규칙(빈 DB·0005·Flyway 관리 DB 통과 / 0004·무관한 DB 거부) |

시험 데이터 `bootstrap/src/test/resources/db/legacy-alembic-0005-snapshot.sql`은 Alembic으로 만든 DB에 legacy 앱을 실제로
띄워 만든 덤프다(파일 헤더에 생성 방법). 이 시험들이 진짜 결함을 잡는지 일부러 V1의 인덱스를 지우거나
baseline 설정을 꺼서 확인했다.

## 새 컨텍스트 모듈을 추가하려면

1. `settings.gradle.kts`에 `include("이름")`, `bootstrap/build.gradle.kts`에 `implementation(project(":이름"))`
2. `<이름>/build.gradle.kts`: 허용된 상류 모듈만 `implementation(project(...))`
3. 기본 패키지에 `@PackageInfo @ApplicationModule(allowedDependencies = [...])` 클래스(`MissionModule.kt` 참고)
4. `ModularityTest`의 `expectedAllowed` 표와 설명 문서(`docs/planning/10 §4`, `13 §2`)를 함께 갱신

## 요구 사항·버전

| 항목 | 버전 | 근거 |
|---|---|---|
| JDK | 21 | `jvmToolchain(21)` |
| Gradle | 9.7.1 (Wrapper, SHA-256 고정) | Spring Boot 4.1.2는 Gradle 8.14+ 또는 9.x 필요 |
| Spring Boot | 4.1.2 | Spring Framework 7.0.x, Jackson 3(`tools.jackson`) |
| Kotlin | 2.3.21 | Spring Boot BOM이 관리하는 버전과 일치 |
| Spring Modulith | 2.1.2 | 정식 릴리스 최신(2.2.0은 RC). 호환은 `ModularityTest`가 증명 |
| ArchUnit | 1.5.1 | 모듈 안 레이어 규칙 |
| Flyway | 12.4.0 | Spring Boot BOM 관리(`flyway-database-postgresql` 필요) |
| PostgreSQL 드라이버 / Hibernate | 42.7.14 / 7.4.13 | Spring Boot BOM 관리, 공간 확장은 `hibernate-spatial` |
| Testcontainers | 2.0.5 | Spring Boot BOM 관리, 이미지 `postgis/postgis:16-3.4-alpine` |

버전은 `gradle/libs.versions.toml`에서만 바꾼다.

## 실행·시험

```bash
cd backend
./gradlew build                                   # 컴파일 + 전체 시험 (Windows는 gradlew.bat)
./gradlew :bootstrap:test --tests "*ModularityTest*"   # 구조 검증만
./gradlew :bootstrap:bootRun                      # 개발 실행 (포트 8080)
curl http://localhost:8080/actuator/health        # {"status":"UP"} (liveness/readiness 그룹 포함)
```

legacy FastAPI(8000)와 나란히 떠야 하므로 포트는 8080이다.

## 규칙

- 컴파일 경고는 오류다(`allWarningsAsErrors`). 경고를 숨기지 말고 원인을 고친다.
- 새 코드에는 작성 이유·목적·연관 코드를 설명하는 주석을 단다(프로젝트 규칙).
- Spring Boot 4는 모듈이 쪼개져 패키지가 3.x와 다르다(예: `org.springframework.boot.health.*`).
  import가 안 풀리면 추측하지 말고 jar에서 실제 위치를 확인한다.
- Modulith는 시험 소스의 클래스를 기본적으로 분석에서 제외한다. 시험 소스의 샘플을 검증하려면
  `ApplicationModules.of(root, ImportOption { true })`처럼 옵션을 줘야 한다.
