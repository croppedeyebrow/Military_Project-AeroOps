import { useActiveMissionRoutesQuery, useGeofencesQuery } from "../../api/missions";
import { useOperationsStore } from "../../store/useOperationsStore";
import { OperationsMapView } from "./OperationsMapView";

/**
 * 실시간 관제용 얇은 래퍼 — 전체 드론 방향 아이콘·호출부호·상태 색상, 실제 이동
 * 경로(실선), 진행 중인 임무의 예정 경로(점선)·구역 폴리곤을 보여준다(4~5단계).
 * 실제 렌더링은 `OperationsMapView`(데이터소스 비의존)가 담당한다 — 재생 화면의
 * `ReplayMap`이 같은 View를 재생 데이터로 감싸는 자매 컴포넌트다.
 */
export function OperationsMap() {
  const assetsById = useOperationsStore((s) => s.assetsById);
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const selectAsset = useOperationsStore((s) => s.selectAsset);
  const { data: missionRoutes } = useActiveMissionRoutesQuery();
  const { data: geofences } = useGeofencesQuery();

  return (
    <OperationsMapView
      assetsById={assetsById}
      selectedAssetId={selectedAssetId}
      onSelectAsset={selectAsset}
      missionRoutes={missionRoutes}
      geofences={geofences}
    />
  );
}
