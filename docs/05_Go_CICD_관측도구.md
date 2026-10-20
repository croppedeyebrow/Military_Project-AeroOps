# Go CI/CD·배포·관측 도구

## 적용 위치

`opsctl`, release verifier, Health Gate와 Prometheus Exporter를 담당한다. GitHub Actions YAML은 Workflow 조정에 사용한다.

## 공부할 개념

- Go module, interface, error wrapping, context
- goroutine, channel, bounded concurrency
- CLI 설계와 idempotent operation
- OCI Image·Digest·Registry API
- SBOM, Cosign, Artifact Attestation
- Health/Readiness와 Canary 판정
- Prometheus Collector와 OpenTelemetry SDK
- graceful shutdown와 rollback 상태 머신

## 적용 원칙

- CI Credential과 운영 배포 Credential을 분리한다.
- 배포는 Tag가 아니라 immutable Digest를 기준으로 한다.
- 검증 실패 시 다음 단계로 진행하지 않는다.
- 운영 도구에 Mission·Command 도메인 규칙을 넣지 않는다.

## 실습

미서명 Image를 거부하고 Canary Health 실패 시 이전 Digest로 복귀한 뒤 실행 증거 Bundle을 생성한다.
