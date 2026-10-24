FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 1단계 보정: 빌드 시 `--build-arg GIT_SHA=$(git rev-parse HEAD) --build-arg IMAGE_TAG=...`로
# 주입하면 GET /system/build-info(deployment 모듈)가 이 값을 그대로 반환한다.
# 값을 주지 않으면 app/core/config.py의 기본값("local-dev")을 쓴다.
ARG GIT_SHA=local-dev
ARG IMAGE_TAG=local-dev
ENV GIT_SHA=${GIT_SHA}
ENV IMAGE_TAG=${IMAGE_TAG}

EXPOSE 8000

# 3단계부터: 빈 환경(볼륨 초기화 등)에서도 기동 시 스키마가 최신 상태이도록
# 실행 전에 migration을 적용한다(`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
