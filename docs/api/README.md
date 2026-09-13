# API 문서

이 폴더는 데이터 계약 사전과, 3단계(수집·저장 파이프라인) 이후 생성되는 OpenAPI 문서·API
참고 자료를 보관한다.

- [`telemetry_frame_dictionary.md`](telemetry_frame_dictionary.md) — Telemetry 채널 계약.
- [`command_envelope_dictionary.md`](command_envelope_dictionary.md) — Command 채널 계약.
- [`examples/`](examples/) — 정상/오류 JSON 예제.
- FastAPI가 자동 생성하는 OpenAPI 스키마는 백엔드 실행 후 `/openapi.json`, `/docs`(Swagger UI)에서 확인할 수 있다.
- 8단계(보안·검증·배포)에서 최종 OpenAPI 문서 스냅샷을 이 폴더에 정리한다.

관련: [[../roadmap/02_단계_데이터계약_시뮬레이터_Day03-04|02_단계_데이터계약_시뮬레이터_Day03-04]], [[../roadmap/08_단계_보안검증_배포_Day19-20|08_단계_보안검증_배포_Day19-20]]
