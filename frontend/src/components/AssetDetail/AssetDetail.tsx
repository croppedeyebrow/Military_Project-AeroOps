import { useOperationsStore } from "../../store/useOperationsStore";
import { classifyFreshness } from "../../types/telemetry";
import { AssetDetailView } from "./AssetDetailView";

/** 실시간 관제용 얇은 래퍼 — 선택 기체의 상세 상태 패널. 지도 선택과 연결한다(4단계).
 * 실제 렌더링은 `AssetDetailView`가 담당한다 — 재생 화면의 `ReplayAssetDetail`이 같은
 * View를 재생 데이터로 감싸는 자매 컴포넌트다. */
export function AssetDetail() {
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const asset = useOperationsStore((s) =>
    s.selectedAssetId ? s.assetsById[s.selectedAssetId] : undefined
  );
  const freshness = asset ? classifyFreshness(asset, Date.now()) : null;

  return (
    <AssetDetailView selectedAssetId={selectedAssetId} asset={asset} freshness={freshness} />
  );
}
