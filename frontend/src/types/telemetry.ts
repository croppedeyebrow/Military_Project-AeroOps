import type { Alert } from "./alert";

/**
 * `backend/app/schemas/telemetry.py`의 `TelemetryFrame`과 1:1 대응.
 * 필드명은 서버가 실제로 보내는 JSON(snake_case) 그대로 쓴다 — 변환 계층을 따로 두면
 * 그 자체가 버그 표면이 되므로, 계약 문서(`docs/api/telemetry_frame_dictionary.md`)와
 * 항상 같은 이름을 유지한다.
 */
export interface TelemetryFrame {
  schema_version: number;
  asset_id: string;
  mission_id: string | null;
  event_time: string;
  received_at: string | null;
  sequence_no: number;

  operation_session_id: string | null;
  deployment_id: string | null;
  correlation_id: string | null;

  latitude: number;
  longitude: number;
  altitude_m: number;

  speed_mps: number | null;
  heading_deg: number | null;
  roll_deg: number | null;
  pitch_deg: number | null;
  yaw_deg: number | null;

  battery_pct: number;
  rssi_dbm: number | null;
  flight_mode: string | null;
}

/** 서버 WebSocket(`/ws/operations`)이 보내는 메시지 종류(`app/modules/realtime/router.py`). */
export type OperationsMessage =
  | { type: "snapshot"; assets: TelemetryFrame[]; alerts: Alert[] }
  | { type: "update"; asset: TelemetryFrame }
  | { type: "alert"; alert: Alert };

/** 프론트에서만 쓰는 파생 상태 — 마지막 수신 후 얼마나 지났는지에 따른 신선도. */
export type AssetFreshness = "live" | "stale" | "disconnected";

/** `docs/planning/01_프론트엔드_아키텍처.md` "검증": 갱신 없이 지나간 시간 기준. */
export const STALE_AFTER_MS = 10_000;
export const DISCONNECTED_AFTER_MS = 60_000;

export function classifyFreshness(frame: TelemetryFrame, nowMs: number): AssetFreshness {
  const lastSeenIso = frame.received_at ?? frame.event_time;
  const lastSeenMs = Date.parse(lastSeenIso);
  const elapsedMs = nowMs - lastSeenMs;

  if (elapsedMs >= DISCONNECTED_AFTER_MS) return "disconnected";
  if (elapsedMs >= STALE_AFTER_MS) return "stale";
  return "live";
}
