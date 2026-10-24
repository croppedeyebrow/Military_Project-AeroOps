# backend — Kotlin·Spring Boot C2 Core

FastAPI(`../legacy-backend/`)를 점진적으로 대체하는 지휘통제(C2) 코어다(ADR 0004). 구조·원칙은
`docs/planning/02_백엔드_아키텍처.md`, 전환 계획은 `docs/new_roadmap/`을 따른다.

## 현재 상태 (2단계 진행 중)

| 모듈 | 역할 | 상태 |
|---|---|---|
| `shared-kernel` | 경계 컨텍스트가 공유하는 ID·값 객체(`AssetId`, `BootId`). Spring·JPA에 의존하지 않는 순수 Kotlin | 완료(2-1) |
| `bootstrap` | Spring Boot 진입점·설정. 업무 규칙은 두지 않는다 | 기동·헬스 확인(2-1) |
| 경계 컨텍스트 6종(mission 등) | Modulith 모듈, `domain/application/adapter-in/adapter-out` | 2-2 예정 |

DB(Flyway/JPA)·보안(OIDC/JWT)·Outbox·관측성(OpenTelemetry)·CI는 후속 유닛에서 추가한다.

## 요구 사항·버전

| 항목 | 버전 | 근거 |
|---|---|---|
| JDK | 21 | `jvmToolchain(21)` |
| Gradle | 9.7.1 (Wrapper, SHA-256 고정) | Spring Boot 4.1.2는 Gradle 8.14+ 또는 9.x 필요 |
| Spring Boot | 4.1.2 | Spring Framework 7.0.x, Jackson 3(`tools.jackson`) |
| Kotlin | 2.3.21 | Spring Boot BOM이 관리하는 버전과 일치 |

버전은 `gradle/libs.versions.toml`에서만 바꾼다.

## 실행·시험

```bash
cd backend
./gradlew build                                   # 컴파일 + 전체 시험 (Windows는 gradlew.bat)
./gradlew :bootstrap:bootRun                      # 개발 실행 (포트 8080)
java -jar bootstrap/build/libs/bootstrap-0.1.0-SNAPSHOT.jar
curl http://localhost:8080/actuator/health        # {"status":"UP"} (liveness/readiness 그룹 포함)
```

legacy FastAPI(8000)와 나란히 떠야 하므로 포트는 8080이다.

## 규칙

- 컴파일 경고는 오류다(`allWarningsAsErrors`). 경고를 숨기지 말고 원인을 고친다.
- Spring Boot 4는 모듈이 쪼개져 패키지가 3.x와 다르다(예: `org.springframework.boot.health.*`).
  import가 안 풀리면 추측하지 말고 jar에서 실제 위치를 확인한다.
