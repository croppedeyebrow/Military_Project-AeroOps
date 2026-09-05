# AeroOps 통합/E2E 테스트

`backend/tests`, `frontend`(vitest), `simulator/tests`는 각 서비스 단위
테스트를 담당한다. 이 폴더는 여러 서비스를 함께 띄운 상태에서 검증하는
통합·E2E 시나리오를 담는다.

- 8단계(`docs/roadmap/08_단계_보안검증_배포_Day1920.md`)에서 핵심 사용자
  시나리오 end-to-end 테스트를 `tests/e2e`에 추가한다.
- 3, 4, 7단계의 정합성/부하/장애 시험 스크립트도 단계가 진행되며 이 폴더에
  누적한다.
