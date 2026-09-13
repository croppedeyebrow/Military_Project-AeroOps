# Deployment 모듈

책임: 실행 중인 코드·이미지·스키마·규칙 버전을 등록·조회한다.

`docs/planning/03_데이터베이스_아키텍처.md` "이벤트·배포 추적성": 모든 telemetry, command,
alert, sync 이벤트에는 `operation_session_id`, `deployment_id`, `schema_version`,
`correlation_id`를 연결한다. 배포 레코드는 변경하지 않고 새 버전으로 추가한다 — 특정 장애
시점에 어떤 코드·컨테이너·규칙·데이터 계약이 사용됐는지 역추적하기 위함이다.

## 구현

- 1단계 보정: `router.py`의 `GET /system/build-info` — `GIT_SHA`, `IMAGE_TAG`, 현재
  alembic head(`schema_version`, DB 연결 없이 계산)를 반환.
- 3단계 보정: `models.py`의 `Deployment`, `EventLog` 테이블 migration만 추가(애플리케이션
  코드는 아직 없음 — `deployments`에 실제로 값을 채우는 자동 등록은 8단계, `event_log`에
  이벤트를 기록하는 로직은 7단계에서 구현한다).

## 로드맵

- 7단계(`docs/roadmap/07_단계_이력재생_관측성_Day16-18.md`): `operation_sessions` 테이블
  추가, `EventLog`에 실제 이벤트 기록 시작, 운용 세션 시작 시 `deployment_id` 고정.
- 8단계(`docs/roadmap/08_단계_보안검증_배포_Day19-20.md`): 배포 시 `deployments` 레코드
  자동 등록(CI/CD 또는 컨테이너 시작 스크립트).

## 예정 구성

- `router.py`에 `POST /deployments`, `GET /deployments`, `POST /operation-sessions` 추가
- `models.py`에 `OperationSession` 추가
