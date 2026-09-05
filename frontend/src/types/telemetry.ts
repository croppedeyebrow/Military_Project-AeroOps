/**
 * backend/app/schemas/telemetry.py의 TelemetryFrame과 대응.
 * 2단계에서 계약이 확정되면 동기화한다.
 */
export interface TelemetryFrame {
  schemaVersion: number;
  assetId: string;
  missionId?: string;
  eventTime: string;
  receivedAt?: string;
  sequenceNo: number;

  latitude: number;
  longitude: number;
  altitudeM: number;

  speedMps?: number;
  headingDeg?: number;
  rollDeg?: number;
  pitchDeg?: number;
  yawDeg?: number;

  batteryPct: number;
  rssiDbm?: number;
  flightMode?: string;
}
