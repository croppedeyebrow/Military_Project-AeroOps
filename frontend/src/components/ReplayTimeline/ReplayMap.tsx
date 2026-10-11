import { OperationsMapView } from "../OperationsMap/OperationsMapView";
import { useReplayStore } from "../../store/useReplayStore";
import type { ReplayDataset } from "../../types/replay";
import { buildAssetFramesAtTime } from "./frameLookup";

interface Props {
  /** 재생 대상 세션의 기체별 이력 — 화면(Unit 4의 재생 탭 컨테이너)이 세션 선택에 맞춰
   * 받아와 넘겨준다. 이 컴포넌트 자신은 데이터를 가져오지 않는다(재생 커서 위치만
   * `useReplayStore`에서 읽는다) — "지금 몇 시인지"는 여러 재생 하위 화면이 공유하는
   * 상태라 store에 두지만, "이 세션의 전체 이력"은 한 번만 받아와 여기로 내려주는 쪽이
   * 중복 계산이 적다. */
  dataset: ReplayDataset;
}

/**
 * 재생 전용 지도 — `OperationsMap`(실시간)과 같은 `OperationsMapView`를 재사용한다.
 * 사용자 결정(2026-10-11): 재생은 실시간 화면과 분리된 별도 탭이지만, 지도를 그리는
 * 로직 자체는 중복 작성하지 않는다.
 *
 * 임무 경로·구역 폴리곤은 넘기지 않는다(Unit 3 범위 밖 — 과거 특정 시점의 경로·구역을
 * 재구성하려면 그 시점 기준 조회가 필요한데, 지금은 "현재" 임무/구역만 조회 가능하다.
 * 재생 중에 지금 임무 경로를 보여주면 오히려 그 시절엔 없었을 정보처럼 혼동을 줄 수
 * 있어 아예 생략한다).
 */
export function ReplayMap({ dataset }: Props) {
  const currentTimeMs = useReplayStore((s) => s.currentTimeMs);
  const selectedAssetId = useReplayStore((s) => s.selectedAssetId);
  const selectAsset = useReplayStore((s) => s.selectAsset);

  const assetsById = currentTimeMs !== null ? buildAssetFramesAtTime(dataset, currentTimeMs) : {};

  return (
    <OperationsMapView
      assetsById={assetsById}
      selectedAssetId={selectedAssetId}
      onSelectAsset={selectAsset}
    />
  );
}
