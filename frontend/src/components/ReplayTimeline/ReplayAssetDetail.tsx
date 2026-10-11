import { AssetDetailView } from "../AssetDetail/AssetDetailView";
import { useReplayStore } from "../../store/useReplayStore";
import type { ReplayDataset } from "../../types/replay";
import { findFrameAtTime } from "./frameLookup";

interface Props {
  dataset: ReplayDataset;
}

/** 재생 전용 상세 패널 — `AssetDetail`(실시간)과 같은 `AssetDetailView`를 재사용한다.
 * `freshness`는 넘기지 않는다(재생 커서 기준 live/stale 개념은 지금 범위 밖 —
 * `ReplayVehicle3DViewer`와 같은 이유). */
export function ReplayAssetDetail({ dataset }: Props) {
  const currentTimeMs = useReplayStore((s) => s.currentTimeMs);
  const selectedAssetId = useReplayStore((s) => s.selectedAssetId);

  const frames = selectedAssetId ? dataset[selectedAssetId] : undefined;
  const asset =
    frames && currentTimeMs !== null ? (findFrameAtTime(frames, currentTimeMs) ?? undefined) : undefined;

  return <AssetDetailView selectedAssetId={selectedAssetId} asset={asset} freshness={null} />;
}
