/** `legacy-backend/app/modules/deployment/router.py`의 `GET /system/build-info` 응답.
 * DB 연결 없이 항상 응답하는 endpoint라 "지금 떠 있는 코드가 뭔지" 확인용으로 가장
 * 가볍다 — `DeploymentBadge`의 "현재" 모드가 쓴다. */
export interface BuildInfo {
  git_sha: string;
  image_tag: string;
  schema_version: string | null;
}

/** `legacy-backend/app/modules/deployment/schemas.py`의 `DeploymentOut`과 1:1 대응.
 * `GET /deployments/{id}`로 특정 배포 하나를 조회할 때 쓴다 — `DeploymentBadge`의
 * "재생 대상" 모드(과거 어느 배포였는지)가 쓴다. */
export interface Deployment {
  id: string;
  git_sha: string;
  image_tag: string;
  schema_version: string | null;
  rule_version: string | null;
  config_version: string | null;
  created_at: string;
}
