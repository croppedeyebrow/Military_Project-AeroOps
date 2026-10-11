import { useAssetCommandsQuery } from "../../api/commands";
import { useOperationsStore } from "../../store/useOperationsStore";
import { classifyFreshness } from "../../types/telemetry";
import { Vehicle3DErrorBoundary } from "./Vehicle3DErrorBoundary";
import { Vehicle3DViewerView } from "./Vehicle3DViewerView";

/**
 * 실시간 관제용 얇은 래퍼 — 실제 렌더링은 `Vehicle3DViewerView`(데이터소스 비의존)가
 * 담당한다. 이 컴포넌트의 책임은 "실시간 store/쿼리에서 데이터를 가져와 props로
 * 넘기는 것"뿐이다. 재생 화면의 `ReplayVehicle3DViewer`가 같은 View를 재생 데이터로
 * 감싸는 자매 컴포넌트다(사용자 결정 2026-10-11: 재생은 실시간 화면과 분리된 별도
 * 탭 — 그래서 View는 공유하되 래퍼는 둘로 나눈다).
 */
function Vehicle3DViewerInner() {
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const asset = useOperationsStore((s) =>
    s.selectedAssetId ? s.assetsById[s.selectedAssetId] : undefined
  );

  const { data: assetCommands } = useAssetCommandsQuery(selectedAssetId);
  const latestCommand = assetCommands?.reduce<(typeof assetCommands)[number] | null>(
    (latest, current) =>
      !latest || Date.parse(current.updated_at) > Date.parse(latest.updated_at) ? current : latest,
    null
  );
  const recentCommandLabel = latestCommand
    ? `최근 연관 명령: ${latestCommand.command_id} · ${latestCommand.status} · ${new Date(
        latestCommand.updated_at
      ).toLocaleTimeString()}`
    : null;

  const freshness = asset ? classifyFreshness(asset, Date.now()) : null;

  return (
    <Vehicle3DViewerView
      selectedAssetId={selectedAssetId}
      asset={asset}
      freshness={freshness}
      recentCommandLabel={recentCommandLabel}
    />
  );
}

/** 오류 경계로 감싼 공개 컴포넌트 — 3D 렌더 실패가 2D 관제를 중단시키지 않는다. */
export function Vehicle3DViewer() {
  return (
    <Vehicle3DErrorBoundary>
      <Vehicle3DViewerInner />
    </Vehicle3DErrorBoundary>
  );
}
