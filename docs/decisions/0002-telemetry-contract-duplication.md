# ADR 0002: TelemetryFrame 계약을 backend/simulator에 각각 구현

- 상태: 승인됨
- 일자: 2026-09-06

## 배경

2단계(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`) 착수 시점에
`simulator/simulator/contracts/__init__.py`에 "backend 스키마를 직접 임포트할지,
JSON Schema를 공유할지 2단계에서 확정한다"는 스텁 코멘트가 남아 있었다. 이를 확정한다.

## 결정

- `backend/app/schemas/telemetry.py`와 `simulator/simulator/contracts/telemetry.py`에
  `TelemetryFrame`을 **각각 독립적으로 구현**한다(코드 중복 허용).
- 두 구현 모두 `schema_version` 필드를 가지며, 데이터 사전
  (`docs/api/telemetry_frame_dictionary.md`)을 단일 진실 공급원(SSOT)으로 삼아 동기화한다.
- 필드·범위 변경 시 두 파일과 데이터 사전을 함께 수정하고, `schema_version`을 올린다.

## 근거

- `simulator/Dockerfile`과 `backend/Dockerfile`은 각각 자신의 폴더만 빌드 컨텍스트로 포함한다
  (`infra/docker-compose.yml`). 컨테이너 경계를 넘는 Python 모듈 임포트는 별도의 공유 패키지
  배포(예: 사내 PyPI, 모노레포 워크스페이스 도구)가 필요해 1인 사이드 프로젝트 규모에서는
  과한 인프라다.
- JSON Schema를 별도 파일로 내보내 양쪽에서 로드하는 방식도 검토했으나, 시뮬레이터는 Pydantic
  모델로 값을 생성하는 쪽(생성 후 검증)이라 JSON Schema만으로는 생성 로직에 도움이 되지 않는다.
- 두 서비스가 독립적으로 배포·버전 관리될 수 있어야 한다는 `02_백엔드_아키텍처.md`의 모듈형
  모놀리스 원칙(서비스 경계 존중)과도 부합한다.

## 영향

- 계약 변경 시 두 파일을 함께 수정해야 하며, 리뷰 체크리스트에 반영한다.
- 향후 서비스가 늘어나 드리프트 위험이 커지면 공유 패키지(`pip install -e ../contracts` 등)로
  전환을 재검토한다.

## 관련 문서

- [[02_단계_데이터계약_시뮬레이터_Day0304]]
- `docs/api/telemetry_frame_dictionary.md`
