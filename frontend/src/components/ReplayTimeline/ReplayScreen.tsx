import type { ReactNode } from "react";
import { useOperationSessionsQuery, useReplayDatasetQuery } from "../../api/replay";
import { useReplayStore } from "../../store/useReplayStore";
import { theme } from "../../styles/theme";
import { DeploymentBadge } from "../DeploymentBadge/DeploymentBadge";
import { TelemetryChart } from "../TelemetryChart/TelemetryChart";
import { ReplayAssetDetail } from "./ReplayAssetDetail";
import { ReplayMap } from "./ReplayMap";
import { ReplayTimeline } from "./ReplayTimeline";
import { ReplayVehicle3DViewer } from "./ReplayVehicle3DViewer";

/**
 * "이력 재생" 탭 전체 화면 — 사용자 결정(2026-10-11): 재생은 실시간 관제와 분리된
 * 별도 탭이다.
 *
 * 이 컨테이너의 책임은 두 가지뿐이다.
 * 1. 고른 세션 구간의 기체별 이력(`useReplayDatasetQuery`)을 **한 번만** 받아
 *    하위 재생 화면(지도·3D·상세)에 `dataset` prop으로 내려준다 — 하위 화면마다
 *    따로 받게 하면 같은 데이터를 각자 들고 있게 된다(TanStack Query가 요청은 합쳐
 *    주지만, "누가 데이터를 소유하는지"가 흐려진다).
 * 2. 레이아웃 — 실시간 탭과 같은 배치(가운데 지도, 오른쪽 3D+상세)를 써서 운영자가
 *    두 탭을 오갈 때 시선 이동이 없게 한다.
 *
 * 재생 대상 배포 버전은 `DeploymentBadge`의 "재생 대상" 모드로 보여준다 — 7단계 완료
 * 기준 "장애 시점의 deployment·규칙 버전을 조회할 수 있다"를 화면에서 바로 확인하는 곳.
 */
export function ReplayScreen() {
  const selectedSessionId = useReplayStore((s) => s.selectedSessionId);
  const rangeStartMs = useReplayStore((s) => s.rangeStartMs);
  const rangeEndMs = useReplayStore((s) => s.rangeEndMs);

  // 세션 목록은 `ReplayTimeline`도 같은 키로 조회한다 — TanStack Query 캐시를 공유하므로
  // 추가 요청 없이 고른 세션의 deployment_id를 얻는다.
  const { data: sessions } = useOperationSessionsQuery();
  const session = sessions?.find((s) => s.id === selectedSessionId) ?? null;

  const range =
    rangeStartMs !== null && rangeEndMs !== null
      ? { startMs: rangeStartMs, endMs: rangeEndMs }
      : null;
  const { data: dataset, isLoading, isError, error } = useReplayDatasetQuery(
    selectedSessionId,
    range
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <ReplayTimeline />

      {session && (
        <div style={{ padding: "0.25rem 1rem", fontSize: "0.85rem", color: "#555" }}>
          <DeploymentBadge deploymentId={session.deployment_id} />
          {dataset && (
            <span style={{ marginLeft: "0.75rem" }}>
              이 구간에 데이터가 있는 기체 {Object.keys(dataset).length}대
            </span>
          )}
        </div>
      )}

      {!selectedSessionId && <Notice>위에서 재생할 운용 세션을 선택하세요.</Notice>}
      {selectedSessionId && isLoading && <Notice>재생 데이터를 불러오는 중…</Notice>}
      {isError && <Notice>재생 데이터를 불러오지 못했습니다: {(error as Error).message}</Notice>}
      {dataset && Object.keys(dataset).length === 0 && (
        <Notice>이 세션 구간에는 수신된 텔레메트리가 없습니다.</Notice>
      )}

      {dataset && Object.keys(dataset).length > 0 && (
        <>
          {/* 컨트롤 바 바로 아래, 지도 위 — 스크럽바와 차트가 같은 시간축을 공유한다는
              느낌을 주려고 전체 폭으로 둔다(지도/3D 옆 칸에 넣으면 좁아서 읽기 어렵다). */}
          <TelemetryChart dataset={dataset} />
          <main style={{ display: "flex", flex: 1, minHeight: 0 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <ReplayMap dataset={dataset} />
            </div>
            <div style={{ width: 340, borderLeft: `1px solid ${theme.color.border.default}`, overflowY: "auto" }}>
              <ReplayVehicle3DViewer dataset={dataset} />
              <hr style={{ border: "none", borderTop: `1px solid ${theme.color.border.subtle}` }} />
              <ReplayAssetDetail dataset={dataset} />
            </div>
          </main>
        </>
      )}
    </div>
  );
}

function Notice({ children }: { children: ReactNode }) {
  return <div style={{ padding: "1rem", color: "gray" }}>{children}</div>;
}
