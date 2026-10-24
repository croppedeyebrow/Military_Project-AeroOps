# 2단계 — Kotlin·Spring Boot 기반 (Day 2~3) — 진행 중

- 시작일: 2026-10-24
- 상태: 2-0 ~ 2-1 완료, 2-2 이후 진행 예정

## 관련 문서

- 계획: [`docs/new_roadmap/02_Kotlin_Spring기반_Day02-03.md`](../../new_roadmap/02_Kotlin_Spring기반_Day02-03.md)
- ADR: [0004](../../decisions/0004-strangler-transition-to-kotlin-c2-core.md), [0005](../../decisions/0005-telemetry-boot-id.md)
- 구조: [`docs/planning/02_백엔드_아키텍처.md`](../../planning/02_백엔드_아키텍처.md)

## 유닛 진행

| 유닛 | 내용 | 상태 |
|---|---|---|
| 2-0 | 레포 구조 변경(`backend/`→`legacy-backend/`), Gradle 9.7.1 Wrapper | 완료 |
| 2-1 | Kotlin·Spring Boot 골격(멀티모듈), 기동·헬스 확인 | 완료 |
| 2-2 | Modulith 경계 컨텍스트 6종, `domain/application/adapter-in/adapter-out`, ArchUnit·Modulith 검증 | 예정 |
| 2-3 | Spring Data JPA + PostgreSQL/PostGIS, Flyway Baseline(빈 DB·기존 DB) | 예정 |
| 2-4 | Security(OIDC/JWT) 골격, Validation, Outbox 골격 | 예정 |
| 2-5 | Actuator·Micrometer·OpenTelemetry·JSON 로그, Testcontainers, CI 잡 | 예정 |

## 구현 내역 (2-0 ~ 2-1)

- `backend/`: Gradle Kotlin DSL 멀티모듈. `gradle/libs.versions.toml`이 버전의 단일 출처.
  - `shared-kernel`: `AssetId`, `BootId`(ADR 0005: 1~64자 `[A-Za-z0-9_-]`, 전환기 `LEGACY` 값) 값 객체.
  - `bootstrap`: Spring Boot 진입점, `application.yml`(포트 8080, liveness/readiness 분리).
- 빌드 규칙: JDK 21 toolchain, `-Xjsr305=strict`, `allWarningsAsErrors`, 어노테이션 대상 규칙
  `-Xannotation-default-target=param-property`.

## 설계 결정

- **버전은 Spring Boot BOM에 맞춘다**: Boot 4.1.2가 관리하는 Kotlin 2.3.21, Jackson 3(`tools.jackson`),
  JUnit 6을 따른다. Gradle은 최신(9.8.2)이 아니라 나온 지 두 달 된 9.7.1을 택했다(Boot 요구 8.14+/9.x 충족).
- **멀티모듈 + 값 객체부터**: 모듈 경계를 컴파일 시점 의존성으로도 강제하기 위해 Gradle 모듈로 나눈다
  (planning/02). 첫 도메인 코드는 ADR 0005의 `BootId`로, 잘못된 값이 생성 시점에 거부된다.
- **경고를 오류로**: 경고를 방치하지 않는다. 실제로 Kotlin 어노테이션 대상 규칙 경고(KT-73255)를 잡아
  컴파일러 옵션으로 해결했다.

## 테스트/검증

- `./gradlew build` 성공. 시험 8건 통과(컨텍스트 기동 1, `AssetId` 2, `BootId` 5).
- 실제 기동(`java -jar`): 2.7초, `/actuator/health` → `UP`(liveness·readiness 그룹 포함).

## 남은 이슈 / 메모

- Spring Boot 4는 모듈 분할로 패키지가 3.x와 다르다(예: 헬스 클래스는 `org.springframework.boot.health.*`).
  Spring Initializr(start.spring.io)가 Kotlin DSL 조합에서 500 오류를 내서 골격은 직접 작성했다.
- HTTP 계층 시험(MockMvc 등)은 Controller를 만들 때 올바른 Boot 4 패키지를 확인해 추가한다.
