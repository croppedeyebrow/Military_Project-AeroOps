import { useEffect } from "react";
import { useAssetsLatestQuery } from "./api/assets";
import { AssetDetail } from "./components/AssetDetail/AssetDetail";
import { AssetList } from "./components/AssetList/AssetList";
import { OperationsMap } from "./components/OperationsMap/OperationsMap";
import { ResyncBanner } from "./components/ResyncBanner/ResyncBanner";
import { useOperationsStore, type ConnectionStatus } from "./store/useOperationsStore";
import { useTelemetryStream } from "./ws/useTelemetryStream";

const CONNECTION_LABEL: Record<ConnectionStatus, string> = {
  connecting: "연결 중…",
  connected: "실시간 연결됨",
  reconnecting: "재연결 시도 중…",
  disconnected: "연결 끊김",
};

const CONNECTION_COLOR: Record<ConnectionStatus, string> = {
  connecting: "goldenrod",
  connected: "seagreen",
  reconnecting: "goldenrod",
  disconnected: "crimson",
};

/**
 * 4단계(2D 실시간 관제) 메인 화면.
 * `docs/planning/01_프론트엔드_아키텍처.md`의 상태 관리 규칙대로, 초기 자산 목록은
 * TanStack Query로 조회하고 실시간 갱신은 WebSocket store가 담당한다.
 */
function App() {
  useTelemetryStream();

  const applySnapshot = useOperationsStore((s) => s.applySnapshot);
  const connectionStatus = useOperationsStore((s) => s.connectionStatus);
  const assetCount = useOperationsStore((s) => Object.keys(s.assetsById).length);

  const { data: initialAssets } = useAssetsLatestQuery();

  // WS 스냅샷이 아직 안 왔을 때만 REST 조회 결과로 먼저 채운다(WS가 도착하면 그걸로
  // 덮어쓴다 — REST는 "빠른 초기 페인트"용, WS가 진실 공급원).
  useEffect(() => {
    if (initialAssets && assetCount === 0) {
      applySnapshot(initialAssets);
    }
  }, [initialAssets, assetCount, applySnapshot]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          padding: "0.5rem 1rem",
          borderBottom: "1px solid #ddd",
        }}
      >
        <h1 style={{ fontSize: "1.1rem", margin: 0 }}>AeroOps 관제</h1>
        <span style={{ color: CONNECTION_COLOR[connectionStatus] }}>
          ● {CONNECTION_LABEL[connectionStatus]}
        </span>
        <span style={{ color: "gray", marginLeft: "auto" }}>기체 {assetCount}대</span>
      </header>

      <ResyncBanner />

      <main style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ width: 280, borderRight: "1px solid #ddd", overflow: "hidden" }}>
          <AssetList />
        </div>
        <div style={{ flex: 1, position: "relative" }}>
          <OperationsMap />
        </div>
        <div style={{ width: 320, borderLeft: "1px solid #ddd", overflowY: "auto" }}>
          <AssetDetail />
        </div>
      </main>
    </div>
  );
}

export default App;
