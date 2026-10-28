# 2단계 — Kotlin·Spring Boot 기반 (Day 2~3) — 진행 중

- 시작일: 2026-10-24
- 상태: 2-0 ~ 2-3 완료(실데이터 리허설은 아래 "남은 이슈" 참고), 2-4 이후 진행 예정

## 관련 문서

- 계획: [`docs/new_roadmap/02_Kotlin_Spring기반_Day02-03.md`](../../new_roadmap/02_Kotlin_Spring기반_Day02-03.md)
- ADR: [0004](../../decisions/0004-strangler-transition-to-kotlin-c2-core.md), [0005](../../decisions/0005-telemetry-boot-id.md)
- 구조·Context Map: [`planning/02`](../../planning/02_백엔드_아키텍처.md), [`planning/10 §4`](../../planning/10_방산_DDD_언어별_책임_아키텍처.md), [`planning/13 §2`](../../planning/13_전환_기준문서_용어_ContextMap_이관표_추적표.md)
- 구현 설명: [`backend/README.md`](../../../backend/README.md)

## 유닛 진행

| 유닛 | 내용 | 상태 |
|---|---|---|
| 2-0 | 레포 구조 변경(`backend/`→`legacy-backend/`), Gradle 9.7.1 Wrapper | 완료 |
| 2-1 | Kotlin·Spring Boot 골격(멀티모듈), 기동·헬스 확인 | 완료 |
| 2-2 | 경계 컨텍스트 6종, Modulith·ArchUnit 구조 검증(3겹 방어선) | 완료 |
| 2-3 | Spring Data JPA + PostgreSQL/PostGIS, Flyway Baseline(빈 DB·기존 DB) | 완료 |
| 2-4 | Security(OIDC/JWT) 골격, Validation, Outbox 골격 | 예정 |
| 2-5 | Actuator·Micrometer·OpenTelemetry·JSON 로그, Testcontainers, CI 잡 | 예정 |

## 구현 내역

### 2-0 ~ 2-1: 골격
- `backend/`: Gradle Kotlin DSL 멀티모듈. `gradle/libs.versions.toml`이 버전의 단일 출처.
- `shared-kernel`: `AssetId`, `BootId`(ADR 0005: 1~64자 `[A-Za-z0-9_-]`, 전환기 `LEGACY` 값).
- `bootstrap`: Spring Boot 진입점, `application.yml`(포트 8080, liveness/readiness 분리).
- 빌드 규칙: JDK 21 toolchain, `-Xjsr305=strict`, `allWarningsAsErrors`, `-Xannotation-default-target=param-property`.

### 2-2: 경계 컨텍스트와 구조 검증
- **모듈 6개**(각각 Gradle 모듈 + `@PackageInfo @ApplicationModule` 클래스):
  `mission`, `operational-picture`, `safety-policy`, `audit`(상류, 의존 대상 없음),
  `command-control`(mission·safety-policy·operational-picture·audit에 의존),
  `incident`(operational-picture·safety-policy·mission·audit에 의존). 선언 그래프는 DAG이고
  `command-control`↔`incident`는 서로 모른다.
- 첫 실제 도메인 코드 `operational-picture/domain/ObservationKey`: ADR 0005의 멱등 키
  `(assetId, bootId, sequenceNo)`. 재부팅 시 같은 `sequenceNo`도 다른 관측으로 구분된다(REQ-TEL-05).
- `bootstrap`의 `@Modulithic(sharedModules = ["shared"])`: 공유 커널을 모든 컨텍스트가 허용 목록 없이 쓰게 하되
  shared-kernel은 프레임워크 비의존으로 유지.
- **구조 검증 시험(bootstrap)**: `ModularityTest`(Modulith: 모듈 간), `LayeringRulesTest`+`LayeringRules`
  (ArchUnit: 모듈 안 — domain 프레임워크 금지, application→adapter 금지, inbound↔outbound 금지).

### 2-3: 영속성 — JPA·PostGIS·Flyway Baseline
- `V1__baseline_from_alembic_0005.sql`: legacy가 Alembic 0001~0005로 만들던 최종 스키마(14 테이블, 14 인덱스,
  7 시퀀스, PostGIS 지오메트리 4개). **손으로 옮기지 않고** Alembic head DB에서 `pg_dump`로 추출해 세션 설정·
  이미지가 만든 확장·`alembic_version`을 제거했다(헤더에 방법 기록).
- `LegacySchemaGuard` + `FlywayMigrationConfig`: `baseline-on-migrate=true`가 엉뚱한 DB를 baseline 처리하는
  위험을 막는 안전장치. 마이그레이션 직전에 "빈 DB / Flyway 관리 DB / Alembic 정확히 0005"일 때만 통과.
- `application.yml`: datasource(환경변수 `C2_DB_*`), `ddl-auto=validate`, `open-in-view=false`, Flyway baseline 설정.
- 시험 데이터 `legacy-alembic-0005-snapshot.sql`: Alembic으로 만든 DB에 legacy 앱을 **실제로 띄워** 텔레메트리 3건·
  명령 1건을 보내 생긴 데이터를 덤프(20행, 9개 테이블).

## 설계 결정

- **baseline 안전장치를 따로 둠**: `baseline-on-migrate`는 "테이블이 있으면 V1을 건너뛴다"일 뿐 DB가 맞는지
  보지 않는다. 설정 실수로 다른 DB를 가리키면 테이블 없이 "성공"하므로, Alembic 0005 확인을 baseline 직전에 넣었다.
- **스키마 파일은 생성물**: V1은 사람이 쓴 DDL이 아니라 실제 Alembic 결과의 추출물이라 누락·오타 위험이 낮고,
  `SchemaEquivalenceTest`가 매번 동등성을 다시 증명한다.
- **인프라 설정은 루트 패키지**: `com.aeroops.c2` 바로 아래 하위 패키지는 Modulith가 업무 모듈로 보기 때문.
- **3겹 방어선**: ① Gradle 의존성(선언 안 한 모듈은 컴파일 불가) ② Spring Modulith(순환·내부 접근·미선언 의존)
  ③ ArchUnit(모듈 안 레이어). 서로 다른 것을 본다.
- **"규칙이 작동한다"를 증명**: 실제 코드에는 모듈 간 import가 아직 없어서 검증이 비어 있는 채로 통과한다.
  그래서 위반 샘플(`archfixture.*`, `com.aeroops.c2` 바깥)에서 검사가 **실패**하고 정상 대조군에서 **통과**하는
  것을 시험한다. 실제 모듈 코드를 일부러 망가뜨려 확인도 했다(아래).
- **패키지 이름**: 설계 문서의 `adapter-in/out`은 `in`이 Kotlin 예약어, 하이픈은 패키지명 불가라서
  `adapter.inbound/outbound`로 구현. `planning/02`에 반영.
- **모듈 기본 패키지 = 공개 API** (Modulith 기본 규칙): 별도 `@NamedInterface` 없이 시작. 하위 패키지는 내부.
- **Modulith 버전**: 2.1.2(정식 최신). 2.2.0은 RC라 제외.

## 테스트/검증

- `./gradlew build` 성공, **시험 42건 통과(건너뜀 0)**: `AssetId` 2, `BootId` 5, `ObservationKey` 4,
  `ModularityTest` 9, `LayeringRulesTest` 7, 그리고 2-3의 마이그레이션 게이트 15건 —
  `FreshDatabaseMigrationTest` 4, `LegacyDatabaseMigrationTest` 4, `SchemaEquivalenceTest` 1, `LegacySchemaGuardTest` 6.
  (DB 시험은 Docker가 없으면 건너뛰므로, 결과 파일에서 건너뜀 0을 확인했다.)
- **게이트 시험이 진짜 결함을 잡는지 변이로 확인(원상복구함)**:
  - V1에서 `CREATE INDEX` 한 줄 삭제 → `SchemaEquivalenceTest` 실패.
  - `baseline-on-migrate: false`로 변경 → `LegacyDatabaseMigrationTest` 4건 실패.
- **실제 코드 위반 실험(2-2 검증, 원상복구함)**:
  - domain 클래스(`ObservationKey`)에 Spring 어노테이션을 붙임 → `LayeringRulesTest` 실패(ArchUnit).
  - `incident`가 `command-control`을 import → `Unresolved reference`로 컴파일 실패(Gradle 의존성).
- 기동 시 `/actuator/health` UP(2-1에서 확인).

## 남은 이슈 / 메모

- **실제 dev DB 복사본 리허설은 미수행**: 로컬 dev DB(Alembic 0005, 텔레메트리 33,121행·event_log 59,154행)를
  읽기 전용으로 덤프해 복사본에 Kotlin 앱을 띄우는 확인을 시도했으나 도구 오류(분류기 무응답)로 완료하지
  못했다. 스냅샷 기반 시험으로 게이트는 충족하지만 실데이터 규모에서의 baseline 확인은 아직 없다.
- **CI**: DB 시험은 Docker가 필요하다. 2-5에서 Kotlin CI 잡을 만들 때 Docker 가능 러너를 쓰고, 건너뜀이
  통과로 보이지 않게 "건너뜀 0" 검사를 넣어야 한다.
- **JPA 엔티티는 아직 없다**: `ddl-auto=validate`는 엔티티가 생기는 3단계부터 실질 검증이 된다.

- 레이어 패키지(`application`, `adapter.*`)는 아직 실제 클래스가 없다(빈 패키지는 git에 남지 않음). 첫 클래스가
  생길 때 만든다. 현재 실제 코드의 Modulith 모듈 간 검증은 의존이 없어 비어 있는 채로 통과하며, 3단계부터
  코드가 생기면 실질 방어선이 된다(위반 샘플이 그때까지의 증거).
- 시험 중 겪은 점: Modulith는 기준 클래스에 `@Modulithic`을 요구하고, 시험 소스 클래스는 기본으로 분석에서
  제외한다(`ImportOption`으로 해결). Spring Boot 4는 모듈이 쪼개져 패키지가 3.x와 다르다.
- Spring Initializr(start.spring.io)가 Kotlin DSL 조합에서 500 오류를 내서 골격은 직접 작성했다.
- HTTP 계층 시험(MockMvc 등)은 Controller를 만들 때 올바른 Boot 4 패키지를 확인해 추가한다.
