import { useEffect, useMemo, useState } from "react";
import { useOperationsStore } from "../../store/useOperationsStore";
import { theme } from "../../styles/theme";
import { classifyFreshness, type AssetFreshness, type TelemetryFrame } from "../../types/telemetry";

const FRESHNESS_LABEL: Record<AssetFreshness, string> = {
  live: "정상",
  stale: "신호 약함",
  disconnected: "단절",
};

// 이 파일에 독립적으로 들어있던 4번째 FRESHNESS_COLOR 사본이었다 — Unit 1에서
// markerElement.ts/App.tsx/AlertPanel.tsx 3곳만 토큰에 연결하고 이 파일을 놓쳤다.
// 지금 발견해서 같이 고친다.
const FRESHNESS_COLOR: Record<AssetFreshness, string> = {
  live: theme.color.status.success,
  stale: theme.color.status.warning,
  disconnected: theme.color.status.neutral,
};

/** 자산(드론) 목록, 검색, 상태 필터. 4단계. */
export function AssetList() {
  const assetsById = useOperationsStore((s) => s.assetsById);
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const selectAsset = useOperationsStore((s) => s.selectAsset);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<AssetFreshness | "all">("all");
  const [, forceTick] = useState(0);

  // 신선도(live/stale/disconnected)는 "지금 몇 시인지"에 따라 바뀌므로 주기적으로
  // 리렌더해서 갱신한다 — 새 텔레메트리가 안 와도 표시가 낡지 않게 한다.
  useEffect(() => {
    const id = setInterval(() => forceTick((n) => n + 1), 2000);
    return () => clearInterval(id);
  }, []);

  const rows = useMemo(() => {
    const now = Date.now();
    const withFreshness: Array<{ asset: TelemetryFrame; freshness: AssetFreshness }> =
      Object.values(assetsById).map((asset) => ({ asset, freshness: classifyFreshness(asset, now) }));

    return withFreshness
      .filter(({ asset }) => asset.asset_id.toLowerCase().includes(search.toLowerCase()))
      .filter(({ freshness }) => statusFilter === "all" || freshness === statusFilter)
      .sort((a, b) => a.asset.asset_id.localeCompare(b.asset.asset_id));
  }, [assetsById, search, statusFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", height: "100%" }}>
      <input
        type="text"
        placeholder="기체 검색"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ padding: "0.4rem" }}
      />
      <select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value as AssetFreshness | "all")}
        style={{ padding: "0.4rem" }}
      >
        <option value="all">전체 상태</option>
        <option value="live">정상</option>
        <option value="stale">신호 약함</option>
        <option value="disconnected">단절</option>
      </select>

      <ul style={{ listStyle: "none", margin: 0, padding: 0, overflowY: "auto", flex: 1 }}>
        {rows.length === 0 && (
          <li style={{ color: "gray", padding: "0.5rem" }}>표시할 기체가 없습니다</li>
        )}
        {rows.map(({ asset, freshness }) => (
          <li
            key={asset.asset_id}
            onClick={() => selectAsset(asset.asset_id)}
            style={{
              padding: "0.5rem",
              cursor: "pointer",
              // 버그 수정(2026-10-12): 다크 테마 전환 전엔 연한 하늘색(#e0f0ff) 배경 +
              // 어두운 기본 글자색이라 괜찮았지만, 전역 글자색이 밝은 색(#e6edf3)으로
              // 바뀌면서 밝은 배경 위에 밝은 글씨가 겹쳐 안 보이게 됐다(실제 스크린샷으로
              // 확인). 선택 배경은 accent 색을 낮은 불투명도로 깔아 어두운 배경에서도
              // 글자色 대비가 유지되게 한다.
              background:
                selectedAssetId === asset.asset_id ? "rgba(34, 211, 238, 0.18)" : "transparent",
              borderLeft:
                selectedAssetId === asset.asset_id
                  ? `3px solid ${theme.color.accent}`
                  : "3px solid transparent",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span
              title={FRESHNESS_LABEL[freshness]}
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: FRESHNESS_COLOR[freshness],
                flexShrink: 0,
              }}
            />
            <span>{asset.asset_id}</span>
            <span style={{ marginLeft: "auto", color: "gray", fontSize: "0.85em" }}>
              {Math.round(asset.battery_pct)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
