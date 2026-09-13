import { useEffect, useState, type CSSProperties } from "react";
import { useOperationsStore } from "../../store/useOperationsStore";

const VISIBLE_DURATION_MS = 4_000;

/**
 * WebSocket이 끊겼다가 다시 붙었을 때("재연결됨, 최신 상태로 복구됨") 잠깐 보여주는
 * 배너. `docs/planning/01_프론트엔드_아키텍처.md`의 `ResyncBanner`에 대응한다.
 *
 * `app.modules.sync`(기체 ↔ 서버 재동기화 handshake)와는 다른 개념이다 — 이건 순수하게
 * "브라우저 ↔ 서버 WebSocket 연결"이 끊겼다 복구된 것을 보여주는 UI 신호다. 기체 쪽
 * 재동기화는 아직 브라우저에서 다룰 화면이 없다(기체 자체를 UI로 조작하지 않으므로).
 */
export function ResyncBanner() {
  const lastReconnectedAt = useOperationsStore((s) => s.lastReconnectedAt);
  const connectionStatus = useOperationsStore((s) => s.connectionStatus);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (lastReconnectedAt === null) return;
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), VISIBLE_DURATION_MS);
    return () => clearTimeout(timer);
  }, [lastReconnectedAt]);

  if (connectionStatus === "reconnecting") {
    return (
      <div style={bannerStyle("goldenrod")}>재연결 시도 중… 최신 상태를 기다리는 중입니다.</div>
    );
  }

  if (visible) {
    return <div style={bannerStyle("seagreen")}>재연결됨 — 최신 상태로 복구했습니다.</div>;
  }

  return null;
}

function bannerStyle(color: string): CSSProperties {
  return {
    padding: "0.5rem 1rem",
    background: color,
    color: "white",
    textAlign: "center",
    fontSize: "0.9rem",
  };
}
