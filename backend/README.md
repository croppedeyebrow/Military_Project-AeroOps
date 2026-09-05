# AeroOps Backend

FastAPI 기반 모듈형 모놀리스. `docs/planning/02_백엔드_아키텍처.md` 참고.

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## 테스트 / 린트

```bash
pytest
ruff check .
mypy app
```

## 모듈 구조

`app/modules/{ingestion,telemetry,mission,alert,realtime,identity,audit}` —
각 모듈 README에 책임과 예정 로드맵 단계를 정리했다.
