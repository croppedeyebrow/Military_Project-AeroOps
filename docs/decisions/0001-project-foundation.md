# ADR 0001: 프로젝트 기반 구조 결정

- 상태: 승인됨
- 일자: 2026-09-05

## 배경

AeroOps는 가상 드론 10대의 텔레메트리를 수집·처리·시각화하는 관제 플랫폼이다.
`docs/planning/00_종합_기획서.md`와 `docs/roadmap/00_20일_개발로드맵.md`에 정의된
20일 로드맵을 기준으로 1단계(프로젝트 기반) 착수 전 모노레포 구조와 기술 스택을 확정한다.

## 결정

- 모노레포 구조: `frontend`, `backend`, `simulator`, `infra`, `docs`, `tests`
- 프론트엔드: React + TypeScript + Vite, 패키지 매니저 npm(기본값)
- 백엔드/시뮬레이터: Python 3.11+, FastAPI, pip + `requirements.txt`(기본값)
- 데이터: PostgreSQL + PostGIS, Redis Streams
- 실행 환경: Docker Compose(로컬), GitHub Actions(CI)
- 관측성: Prometheus + Grafana

## 근거

- 기획서에 명시된 기술 스택을 그대로 채택하여 이후 단계 문서와의 일관성을 유지한다.
- 패키지 매니저는 팀 규모(1인 사이드 프로젝트)를 고려해 학습 비용이 낮은 기본값(npm, pip)을 선택한다.
- 단일 FastAPI 애플리케이션 내부의 모듈형 모놀리스로 시작하여 초기 복잡도를 낮춘다(`02_백엔드_아키텍처.md`).

## 영향

- 이후 마이크로서비스로 분리가 필요할 경우 `backend/app/modules/*` 경계를 기준으로 분리한다.
- pnpm/Poetry로 전환 시 CI 워크플로우(`.github/workflows/ci.yml`)와 Dockerfile의 설치 명령을 함께 수정해야 한다.

## 관련 문서

- [[00_종합_기획서]]
- [[00_20일_개발로드맵]]
