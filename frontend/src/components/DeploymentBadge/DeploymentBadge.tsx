import type { CSSProperties } from "react";
import { useBuildInfoQuery, useDeploymentQuery } from "../../api/deployments";
import { formatDeploymentLabel } from "./format";

interface Props {
  /** 생략하면 "현재" 모드 — `GET /system/build-info`로 지금 떠 있는 코드 버전을 보여준다.
   * 지정하면 "재생 대상" 모드 — `GET /deployments/{id}`로 그 특정 배포(과거 버전일 수
   * 있음)의 버전을 보여준다. 완료 기준 "장애 시점의 deployment·규칙버전을 조회할 수
   * 있다"가 요구하는 두 가지 쓰임을 하나의 컴포넌트로 both 처리한다 — 두 모드가 보여줄
   * 내용의 모양(버전 라벨)이 완전히 같아서 따로 컴포넌트를 둘 이유가 없다. */
  deploymentId?: string;
}

/**
 * 현재 또는 특정 배포의 버전(git SHA·이미지 태그)을 짧게 보여주는 배지.
 * 7단계(`docs/roadmap/07_단계_이력재생_관측성_Day16-18.md`) — 재생 화면(`ReplayTimeline`)
 * 이 아직 없어 지금은 "현재" 모드만 실제로 쓰이지만, `deploymentId`를 받는 모드는 재생
 * 화면이 그대로 가져다 쓸 수 있게 미리 준비해둔다.
 */
export function DeploymentBadge({ deploymentId }: Props) {
  // 두 모드 중 하나만 활성 쿼리가 돈다(useBuildInfoQuery는 deploymentId가 있어도 계속
  // 돌지만 화면에는 쓰지 않는다 — 훅을 조건부로 호출할 수 없다는 React 규칙 때문에
  // "항상 두 훅을 부르고 보여줄 것만 고른다"는 흔한 패턴을 쓴다).
  const buildInfo = useBuildInfoQuery();
  const deployment = useDeploymentQuery(deploymentId ?? null);

  if (deploymentId) {
    if (deployment.isLoading || !deployment.data) {
      return <span style={badgeStyle}>배포 정보 조회 중…</span>;
    }
    return (
      <span style={badgeStyle} title={`deployment_id: ${deploymentId}`}>
        재생 대상 · {formatDeploymentLabel(deployment.data)}
      </span>
    );
  }

  if (buildInfo.isLoading || !buildInfo.data) {
    return <span style={badgeStyle}>버전 확인 중…</span>;
  }
  return (
    <span style={badgeStyle} title={`schema_version: ${buildInfo.data.schema_version ?? "—"}`}>
      {formatDeploymentLabel(buildInfo.data)}
    </span>
  );
}

const badgeStyle: CSSProperties = {
  padding: "0.15rem 0.5rem",
  borderRadius: "4px",
  background: "#eee",
  color: "#555",
  fontSize: "0.8rem",
  fontFamily: "monospace",
};
