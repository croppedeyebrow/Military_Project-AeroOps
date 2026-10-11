import { Vehicle3DErrorBoundary } from "../Vehicle3DViewer/Vehicle3DErrorBoundary";
import { Vehicle3DViewerView } from "../Vehicle3DViewer/Vehicle3DViewerView";
import { useReplayStore } from "../../store/useReplayStore";
import type { ReplayDataset } from "../../types/replay";
import { findFrameAtTime } from "./frameLookup";

interface Props {
  dataset: ReplayDataset;
}

/**
 * 재생 전용 3D 뷰어 — `Vehicle3DViewer`(실시간)와 같은 `Vehicle3DViewerView`를
 * 재사용한다. `ReplayMap`과 같은 이유로 지도/3D 렌더링 로직은 중복 작성하지 않는다.
 *
 * `freshness`와 `recentCommandLabel`은 둘 다 넘기지 않는다(View에 `null`/`undefined`로
 * 전달돼 해당 UI가 숨겨진다) — 둘 다 "지금 몇 시냐"를 전제로 하는 개념인데
 * (`classifyFreshness`는 실제 현재 시각과 비교, 명령 연관은 "최근"이 현재 기준) 재생
 * 중엔 "지금"이 재생 커서 시각이라 의미가 달라진다. 지금 단계에서는 혼동을 피하려고
 * 아예 생략한다 — 필요해지면 재생 커서 기준으로 재계산하는 버전을 추가한다.
 */
export function ReplayVehicle3DViewer({ dataset }: Props) {
  const currentTimeMs = useReplayStore((s) => s.currentTimeMs);
  const selectedAssetId = useReplayStore((s) => s.selectedAssetId);

  const frames = selectedAssetId ? dataset[selectedAssetId] : undefined;
  const asset =
    frames && currentTimeMs !== null ? (findFrameAtTime(frames, currentTimeMs) ?? undefined) : undefined;

  return (
    <Vehicle3DErrorBoundary>
      <Vehicle3DViewerView selectedAssetId={selectedAssetId} asset={asset} freshness={null} />
    </Vehicle3DErrorBoundary>
  );
}
