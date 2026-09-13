import { useEffect, useMemo, useState } from "react";
import { useOperationsStore } from "../../store/useOperationsStore";
import { classifyFreshness, type AssetFreshness, type TelemetryFrame } from "../../types/telemetry";

const FRESHNESS_LABEL: Record<AssetFreshness, string> = {
  live: "정상",
  stale: "신호 약함",
  disconnected: "단절",
};

const FRESHNESS_COLOR: Record<AssetFreshness, string> = {
  live: "seagreen",
  stale: "goldenrod",
  disconnected: "gray",
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
              background: selectedAssetId === asset.asset_id ? "#e0f0ff" : "transparent",
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
