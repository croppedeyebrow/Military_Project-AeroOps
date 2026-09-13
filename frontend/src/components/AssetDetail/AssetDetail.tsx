import { useOperationsStore } from "../../store/useOperationsStore";
import { classifyFreshness, type TelemetryFrame } from "../../types/telemetry";

const FIELD_LABEL: Partial<Record<keyof TelemetryFrame, string>> = {
  sequence_no: "sequence_no",
  event_time: "이벤트 시각",
  received_at: "서버 수신 시각",
  mission_id: "임무",
  latitude: "위도",
  longitude: "경도",
  altitude_m: "고도(m)",
  speed_mps: "속도(m/s)",
  heading_deg: "진행방향(°)",
  roll_deg: "roll(°)",
  pitch_deg: "pitch(°)",
  yaw_deg: "yaw(°)",
  battery_pct: "배터리(%)",
  rssi_dbm: "RSSI(dBm)",
  flight_mode: "비행 모드",
};

/** 선택 기체의 상세 상태 패널. 지도 선택과 연결한다(4단계). */
export function AssetDetail() {
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const asset = useOperationsStore((s) =>
    s.selectedAssetId ? s.assetsById[s.selectedAssetId] : undefined
  );

  if (!selectedAssetId) {
    return (
      <div style={{ padding: "1rem", color: "gray" }}>
        지도 또는 목록에서 기체를 선택하세요.
      </div>
    );
  }

  if (!asset) {
    return (
      <div style={{ padding: "1rem", color: "gray" }}>
        {selectedAssetId}의 데이터를 아직 받지 못했습니다.
      </div>
    );
  }

  const freshness = classifyFreshness(asset, Date.now());

  return (
    <div style={{ padding: "1rem" }}>
      <h3 style={{ marginTop: 0 }}>{asset.asset_id}</h3>
      <p style={{ color: freshness === "live" ? "seagreen" : "goldenrod" }}>
        {freshness === "live" ? "실시간 수신 중" : freshness === "stale" ? "신호 약함" : "통신 단절"}
      </p>
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "0.25rem 0.75rem" }}>
        {(Object.entries(FIELD_LABEL) as [keyof TelemetryFrame, string][]).map(([key, label]) => (
          <FieldRow key={key} label={label} value={asset[key]} />
        ))}
      </dl>
    </div>
  );
}

function FieldRow({ label, value }: { label: string; value: unknown }) {
  return (
    <>
      <dt style={{ color: "gray" }}>{label}</dt>
      <dd style={{ margin: 0 }}>{value === null || value === undefined ? "—" : String(value)}</dd>
    </>
  );
}
