/**
 * Git SHA를 배지에 표시할 짧은 형태로 줄인다.
 *
 * 목적/근거: 전체 SHA(40자)는 배지에 넣기엔 너무 길다 — GitHub 등 대부분의 도구가
 * 관례적으로 쓰는 7~10자 축약을 따른다(실제로는 Git이 보장하는 "충돌 없는 최소 길이"가
 * 아니라 "사람이 읷기 좋은 길이"일 뿐이라, 이 축약값을 다시 서버에 조회 키로 쓰지 않는다
 * — 배지는 항상 전체 `deployment_id`나 `git_sha`를 함께 들고 있다가 그걸로 조회한다).
 * 기본값을 10으로 둔 이유: 로컬 개발 placeholder 값인 `"local-dev"`(9자)가 억지로
 * 잘려서 `"local-de"`처럼 덜 읽히게 보이지 않게 하면서도, 실제 40자 SHA는 충분히
 * 줄여준다.
 */
export function shortenGitSha(gitSha: string, length = 10): string {
  return gitSha.length <= length ? gitSha : gitSha.slice(0, length);
}

export interface DeploymentLike {
  git_sha: string;
  image_tag: string;
}

/** 배지 본문 텍스트. "git_sha · image_tag" 형태 — 둘 다 "이 코드가 정확히 뭔지"를
 * 구성하는 축이라 하나만 보여주면 역추적에 부족하다(이미지 태그가 같아도 SHA가 다른
 * 핫픽스가 있을 수 있고, 반대도 가능). */
export function formatDeploymentLabel(deployment: DeploymentLike): string {
  return `${shortenGitSha(deployment.git_sha)} · ${deployment.image_tag}`;
}
