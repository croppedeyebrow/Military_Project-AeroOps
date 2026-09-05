# AeroOps Infra

Docker Compose 기반 로컬 실행 환경. `docs/planning/04_인프라_네트워크_클라우드.md` 참고.

## 실행

```bash
cp infra/.env.example infra/.env
cp backend/.env.example backend/.env
cp simulator/.env.example simulator/.env
cp frontend/.env.example frontend/.env
docker compose -f infra/docker-compose.yml --env-file infra/.env up --build
```

- API: http://localhost:8000 (`/health/live`, `/health/ready`, `/docs`)
- Web: http://localhost:5173 (dev) 또는 http://localhost (compose 정적 서빙)
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

`reverse-proxy`는 선택적 서비스이며, 데모 배포 시 활성화한다.
