# DeploymentBadge

현재 또는 특정 배포(git SHA·이미지 태그·schema_version)를 짧게 보여주는 배지.
7단계(`docs/roadmap/07_단계_이력재생_관측성_Day16-18.md`)에서 구현.

## 두 모드

- `<DeploymentBadge />`(prop 없음): `GET /system/build-info`로 "지금 이 코드가 어떤
  버전인지"를 보여준다. 헤더에 상시 표시한다.
- `<DeploymentBadge deploymentId="deploy-abcd1234" />`: `GET /deployments/{id}`로 그
  특정(과거일 수 있는) 배포 버전을 보여준다. `ReplayTimeline`이 아직 없어 지금은
  실제로 쓰이는 곳이 없지만, 재생 화면이 "이 구간은 어느 배포였다"를 보여줄 때
  그대로 가져다 쓸 수 있게 미리 만들어뒀다.

## 파일

- `format.ts`: git SHA 축약, 라벨 포맷팅 순수 함수(`format.test.ts`로 검증, DOM 불필요).
- `DeploymentBadge.tsx`: 위 두 모드를 처리하는 컴포넌트.

## 의도적으로 하지 않은 것

- 배지 클릭 시 상세 팝오버(변경 이력, rule_version 등): 지금은 `title` 속성(hover
  tooltip)으로만 schema_version/deployment_id를 노출한다. 필요해지면 `AuditLog` 조회
  패널처럼 별도 상세 화면을 만든다.
