# AeroOps

가상 드론 10대의 위치·자세·기체 상태를 실시간 수집하여 임무 상태, 이상 이벤트,
운용 이력을 관리하는 관제 플랫폼. 전체 기체는 2D 지도 심벌로, 선택 기체는 3D
모델로 표현한다. 자세한 내용은 [`docs/planning/00_종합_기획서.md`](docs/planning/00_종합_기획서.md) 참고.

> 현재 상태: **2단계 — 데이터 계약·시뮬레이터 구현 완료.** `TelemetryFrame` 계약
> (백엔드/시뮬레이터 양쪽 검증), 원형·직선·경유지 비행 시나리오, seed 기반 재현
> 가능한 10대 생성기, 7종 장애 주입기를 갖췄다. 실제 수집 API(`POST /telemetry`)는
> 3단계에서 구현되므로 현재 시뮬레이터는 `--sink stdout`으로 독립 검증한다. 진행
> 상황은 [`docs/dev_history/`](docs/dev_history/), 전체 계획은
> [`docs/roadmap/00_20일_개발로드맵.md`](docs/roadmap/00_20일_개발로드맵.md) 참고.

## 구조

```
AeroOps/
├── frontend/    React + TypeScript + Vite 관제 UI
├── backend/     FastAPI 모듈형 모놀리스
├── simulator/   Python 드론 텔레메트리 시뮬레이터
├── infra/       Docker Compose, Prometheus, Grafana, reverse proxy
├── tests/       서비스 간 통합/E2E 테스트
└── docs/
    ├── planning/     기획·아키텍처 문서 (프론트/백엔드/DB/인프라/데이터엔지니어링)
    ├── roadmap/      20일 단계별 개발 로드맵과 작업 분해
    ├── decisions/    기술 결정 기록(ADR)
    ├── dev_history/  단계별 개발 내역 기록
    └── api/          데이터 계약·API 문서(OpenAPI는 3단계 이후 생성)
```

## 기술 스택

| 영역 | 기술 |
|---|---|
| 프론트 | React, TypeScript, Vite, MapLibre, Three.js |
| 백엔드 | FastAPI, Pydantic, WebSocket |
| 이벤트 | Redis Streams |
| 데이터 | PostgreSQL, PostGIS |
| 관측성 | Prometheus, Grafana |
| 실행 | Docker Compose, GitHub Actions |

## 로컬 실행

```bash
cp infra/.env.example infra/.env
cp backend/.env.example backend/.env
cp simulator/.env.example simulator/.env
cp frontend/.env.example frontend/.env

docker compose -f infra/docker-compose.yml --env-file infra/.env up --build
```

- API: http://localhost:8000/health/ready, http://localhost:8000/docs
- Web: http://localhost:5173 (`npm run dev`로 직접 실행 시) 또는 compose의 5173 포트
- Grafana: http://localhost:3000, Prometheus: http://localhost:9090

시뮬레이터는 기본적으로 실행되지 않는다(`profiles: with-simulator`). 실제 비행
시나리오·장애 주입 로직은 2단계에서 구현되었지만, 수집 API(`POST /telemetry`)가
아직 없는 3단계 이전에는 전송이 실패 로그만 남기고 넘어간다:

```bash
docker compose -f infra/docker-compose.yml --profile with-simulator up
```

서비스별 개발 방법은 각 폴더의 README(`frontend/README.md`,
`backend/README.md`, `simulator/README.md`, `infra/README.md`)를 참고한다.

## 로드맵

| 단계 | 기간 | 목표 |
|---|---:|---|
| 1 | Day 1~2 | 프로젝트 기반 |
| 2 | Day 3~4 | 데이터 계약·시뮬레이터 |
| 3 | Day 5~7 | 수집·저장 파이프라인 |
| 4 | Day 8~10 | 2D 실시간 관제 |
| 5 | Day 11~13 | 임무·경보 관리 |
| 6 | Day 14~15 | 3D 상세 뷰어 |
| 7 | Day 16~18 | 이력 재생·관측성 |
| 8 | Day 19~20 | 보안·검증·배포 |

각 단계의 작업/완료 기준/산출물은 `docs/roadmap/`의 해당 문서를 참고한다.

## 기술 결정 기록

주요 아키텍처 결정은 `docs/decisions/`에 ADR 형식으로 기록한다. 매일 실행법과
결정 기록을 함께 갱신한다(로드맵 일정 원칙).

## 제외 범위

실제 기체 제어, SLAM, 군집제어, 실시간 영상 AI, CAD급 모델링, Kubernetes는
MVP에서 제외한다.
