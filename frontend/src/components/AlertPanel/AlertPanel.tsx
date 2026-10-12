import { useMemo, useState } from "react";
import { useAcknowledgeAlert, useResolveAlert } from "../../api/alerts";
import { useOperationsStore } from "../../store/useOperationsStore";
import { theme } from "../../styles/theme";
import type { Alert } from "../../types/alert";

const SEVERITY_COLOR: Record<string, string> = {
  WARNING: theme.color.status.warning,
  CRITICAL: theme.color.status.danger,
};

const ALERT_TYPE_LABEL: Record<string, string> = {
  BATTERY_LOW: "배터리 부족",
  RSSI_LOW: "통신 신호 저하",
  GEOFENCE_BREACH: "구역 이탈",
};

/** 경보 패널. `/ws/operations`의 스냅샷·실시간 "alert" 메시지로 채워진다(4~5단계). */
export function AlertPanel() {
  const alertsById = useOperationsStore((s) => s.alertsById);
  const [showResolved, setShowResolved] = useState(false);
  const acknowledge = useAcknowledgeAlert();
  const resolve = useResolveAlert();

  const alerts = useMemo(() => {
    const all = Object.values(alertsById);
    const filtered = showResolved ? all : all.filter((a) => a.status !== "RESOLVED");
    return filtered.sort((a, b) => Date.parse(b.triggered_at) - Date.parse(a.triggered_at));
  }, [alertsById, showResolved]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", padding: "0.5rem", gap: "0.5rem" }}>
        <strong>경보</strong>
        <span style={{ color: "gray" }}>
          (미해결 {Object.values(alertsById).filter((a) => a.status !== "RESOLVED").length})
        </span>
        <label style={{ marginLeft: "auto", fontSize: "0.85em", color: "gray" }}>
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
          />{" "}
          해제됨 포함
        </label>
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, overflowY: "auto", flex: 1 }}>
        {alerts.length === 0 && (
          <li style={{ color: "gray", padding: "0.5rem" }}>표시할 경보가 없습니다</li>
        )}
        {alerts.map((alert) => (
          <AlertRow
            key={alert.id}
            alert={alert}
            onAcknowledge={() =>
              acknowledge.mutate({ alertId: alert.id, acknowledgedBy: "operator" })
            }
            onResolve={() => resolve.mutate({ alertId: alert.id, resolvedBy: "operator" })}
          />
        ))}
      </ul>
    </div>
  );
}

function AlertRow({
  alert,
  onAcknowledge,
  onResolve,
}: {
  alert: Alert;
  onAcknowledge: () => void;
  onResolve: () => void;
}) {
  return (
    <li
      style={{
        padding: "0.5rem",
        borderBottom: `1px solid ${theme.color.border.subtle}`,
        fontSize: "0.9em",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: SEVERITY_COLOR[alert.severity] ?? "gray",
          }}
        />
        <strong>{ALERT_TYPE_LABEL[alert.alert_type] ?? alert.alert_type}</strong>
        <span style={{ color: "gray" }}>{alert.asset_id}</span>
        <span style={{ marginLeft: "auto", color: "gray" }}>{alert.status}</span>
      </div>
      <div style={{ color: "gray", fontSize: "0.85em" }}>
        {Object.entries(alert.evidence)
          .map(([k, v]) => `${k}=${v}`)
          .join(", ")}{" "}
        · rule {alert.rule_version}
      </div>
      {alert.status === "OPEN" && (
        <button onClick={onAcknowledge} style={{ marginTop: "0.25rem" }}>
          확인
        </button>
      )}
      {alert.status === "ACKNOWLEDGED" && (
        <button onClick={onResolve} style={{ marginTop: "0.25rem" }}>
          해제
        </button>
      )}
    </li>
  );
}
