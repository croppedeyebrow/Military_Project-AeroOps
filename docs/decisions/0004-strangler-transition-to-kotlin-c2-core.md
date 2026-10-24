# ADR 0004: FastAPI에서 Kotlin C2 Core로의 점진적(Strangler) 전환

- 상태: **승인됨** (2026-10-24, 사용자 승인. 공존 기간 스키마 소유는 제안과 달리 **Kotlin(Flyway)** 으로 변경)
- 일자: 2026-10-20
- 대체 대상: [ADR 0001](0001-project-foundation.md)의 "백엔드: FastAPI 단일 모듈형 모놀리스" 결정(프론트·DB·Redis·관측성 결정은 유지)

## 배경

FastAPI 기반 1~7단계가 구현·검증됐다(`docs/dev_history/legacy/`). 기획 문서가 핵심 백엔드를
Kotlin/Spring Modulith로, 통신을 Rust로, 시뮬레이터를 C++로, 배포·관측 도구를 Go로,
Python을 AI·MLOps로 재배치하는 방향으로 바뀌었다
(`docs/planning/10~12`, `docs/new_roadmap/`).

## 결정

1. **Big-bang 재작성을 하지 않는다.** React와 장비 계약 앞에 호환 경계를 두고 조회
   Projection → Mission → Command 순으로 System of Record를 옮긴다.
2. **한 Context의 쓰기 주체는 항상 하나다.** FastAPI와 Kotlin이 같은 테이블에 동시에
   쓰는 Dual Write를 금지한다. 쓰기 권한 이전은 Context 단위로 한 번에 한다.
3. **검증 전에는 FastAPI 코드를 삭제하지 않는다.** 제거는 완전 Replay 2회 이상과 장애
   회귀시험 통과 후 별도 결정한다.
4. **현행 동작을 기준선으로 고정한다.** Contract Snapshot과 Golden Replay를 먼저 만들고,
   Kotlin 구현은 같은 시험을 통과해야 한다(`docs/planning/11`의 보존 불변조건 8개).
5. **언어별 단일 책임을 따른다.** Kotlin=임무·C2·상황도·정책·감사, Rust=장비 통신
   경계, C++=결정적 시뮬레이터·Replay, Python=AI·MLOps, Go=배포 검증·운영 도구.
   업무 규칙은 Kotlin 밖에 복제하지 않는다.

## 확정 사항 (2026-10-24)

### 레포 구조

- **`backend/`는 Kotlin·Spring Boot(Gradle 멀티모듈)가 차지한다**(`docs/planning/02` 코드 구조와 일치).
- 현행 FastAPI는 **`legacy-backend/`로 이동**한다. 삭제하지 않는다(결정 3번: 검증 전 삭제 금지,
  Golden Replay·계약 기준선의 비교 대상이자 전환 기간 운영 구현).
- Compose 서비스: 기존 `api`는 `legacy-backend`를 빌드하고, Kotlin은 새 서비스 `c2-core`로 추가한다.

### 공존 기간 기본값

| 쟁점 | 결정 | 이유 |
|---|---|---|
| 공존 기간 스키마 소유 | **Kotlin(Flyway)이 모든 DDL을 소유한다.** Alembic은 head `0005`에서 동결한다. Flyway Baseline은 Alembic 0001~0005 결과와 동일하며, 빈 DB는 baseline 마이그레이션이 만들고 기존 DB는 baseline 버전으로 등록한다. | 마이그레이션 도구가 하나여야 이중 DDL 충돌이 없다. |
| Shadow의 Redis 소비 | Kotlin은 별도 consumer group으로 같은 Stream을 읽는다(FastAPI group과 분리) | 이중 소비로 인한 메시지 누락·중복 방지 |
| Wire 프로토콜 | 기존 HTTP+JSON을 기준선으로 유지하고, Rust Gateway 도입 시 JSON을 먼저 지원, Protobuf는 Adapter에서 양쪽 지원 후 전환 | 기준선 비교 가능성 유지 |
| Rust 시험 클라이언트 | C++ 시뮬레이터 완성 전에는 기존 Python 시뮬레이터에 Gateway 어댑터를 붙여 시험 | Day 8~9와 Day 10~11 순서 의존 해소 |
| 시뮬레이터 명령 반응 | `simulator/device_loop.py`의 RTL/MOVE_TO/LOITER/ARM/DISARM/SET_ALTITUDE/SET_SPEED 반응을 C++ 이관 범위와 완료 게이트에 포함 | 이관 시 기능 퇴보 방지 |

## 영향

- **스키마 소유 이전의 파급(legacy 호환 규칙)**: Flyway가 DDL을 소유한 뒤에도 `legacy-backend`는 같은 DB를
  계속 쓴다. 따라서 legacy가 쓰기 주체인 Context의 테이블에 대한 Flyway 변경은 **legacy 코드가 깨지지 않는
  Expand 전용**(컬럼 추가·기본값 있는 NOT NULL·새 테이블)이어야 한다. 제약 교체·컬럼 삭제 같은 Contract
  변경은 해당 Context의 쓰기 주체가 Kotlin으로 넘어간 뒤에만 한다. legacy 테스트용 `alembic upgrade head`는
  baseline과 동치인 0005까지만 유지한다.
- `boot_id`가 Wire 계약 필수 필드가 되므로 backend `TelemetryFrame`, DB, simulator 변경이
  필요하다(1-4 유닛에서 범위 확정).
- 기존 20일 로드맵(`docs/roadmap/`)은 "완료된 FastAPI 기준선"이 되고, 이후 일정은
  `docs/new_roadmap/`을 따른다.
- 모든 Cutover는 Shadow 비교 → Canary → 쓰기 이전 → Rollback 경로 확보 순서를 따른다.

## 관련 문서

- `docs/planning/10_방산_DDD_언어별_책임_아키텍처.md`
- `docs/planning/11_현행레포_분석과_전환범위.md`
- `docs/planning/12_점진적_전환_아키텍처.md`
- `docs/new_roadmap/00_14일_전환로드맵.md`
