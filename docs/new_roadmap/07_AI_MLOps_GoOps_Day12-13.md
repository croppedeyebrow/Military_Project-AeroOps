# 7단계 — Python AI·MLOps와 Go Ops (Day 12~13)

## 목표

AI를 명령 경로에서 격리하고 모델·배포 수명주기를 운영 가능한 형태로 연결한다.

## Python 작업

- Versioned Feature Contract와 Window Feature
- 규칙·EWMA·Isolation Forest 기준 모델 비교
- 시간·기체·비행 단위 Dataset 분할
- MLflow Dataset·Run·Model·Prompt·Knowledge Lineage
- 로컬 GGUF/llama.cpp Adapter
- FTS+pgvector Hybrid Retrieval과 근거 ID 출력
- `INSUFFICIENT_EVIDENCE`와 규칙 기반 Fallback

## Go 작업

- `opsctl`의 preflight, verify, deploy, health, rollback
- OCI Digest, SBOM, Cosign Signature 검증
- 배포·Gateway·AI Fallback Metric Exporter
- 다언어 CI Matrix와 Artifact Metadata 수집

## 완료 게이트

AI 중단 시 C2 Core가 정상 동작하고, 승인되지 않은 모델·미서명 이미지는 로드 또는 배포되지 않는다.
