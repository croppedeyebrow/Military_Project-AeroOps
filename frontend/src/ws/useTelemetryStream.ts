import { useEffect, useRef } from "react";
import { useOperationsStore } from "../store/useOperationsStore";
import type { OperationsMessage } from "../types/telemetry";
import { computeBackoffDelayMs } from "./backoff";

const DEFAULT_WS_URL = "ws://localhost:8000/ws/operations";

/**
 * `/ws/operations` 구독.
 *
 * 4단계(`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`): 연결이 끊기면 지수 백오프로
 * 재연결한다. 서버는 매 연결마다 전체 스냅샷을 새로 보내주므로(`app/modules/realtime/
 * router.py`), 별도 "resume" 프로토콜 없이 재연결만으로 최신 상태가 복구된다 —
 * 재연결이었다면 store에 `markReconnected()`로 표시해 `ResyncBanner`가 잠깐 보여줄 수
 * 있게 한다.
 *
 * 장기 이력을 브라우저에 쌓지 않는다 — 매 메시지를 store의 "최신 프레임 하나"에만
 * 반영한다(`docs/planning/01_프론트엔드_아키텍처.md`).
 */
export function useTelemetryStream(): void {
  const applySnapshot = useOperationsStore((s) => s.applySnapshot);
  const applyUpdate = useOperationsStore((s) => s.applyUpdate);
  const applyAlert = useOperationsStore((s) => s.applyAlert);
  const setConnectionStatus = useOperationsStore((s) => s.setConnectionStatus);
  const markReconnected = useOperationsStore((s) => s.markReconnected);

  const attemptRef = useRef(0);
  const hasConnectedBeforeRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || DEFAULT_WS_URL;
    unmountedRef.current = false;

    const connect = (): void => {
      if (unmountedRef.current) return;
      setConnectionStatus(attemptRef.current === 0 ? "connecting" : "reconnecting");

      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        if (hasConnectedBeforeRef.current) {
          markReconnected();
        }
        hasConnectedBeforeRef.current = true;
        attemptRef.current = 0;
        setConnectionStatus("connected");
      };

      socket.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as OperationsMessage;
        if (message.type === "snapshot") {
          applySnapshot(message.assets, message.alerts);
        } else if (message.type === "update") {
          applyUpdate(message.asset);
        } else {
          applyAlert(message.alert);
        }
      };

      socket.onclose = () => {
        socketRef.current = null;
        if (unmountedRef.current) return;
        setConnectionStatus("disconnected");
        const delay = computeBackoffDelayMs(attemptRef.current + 1);
        attemptRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      unmountedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      socketRef.current?.close();
    };
  }, [applySnapshot, applyUpdate, applyAlert, setConnectionStatus, markReconnected]);
}
