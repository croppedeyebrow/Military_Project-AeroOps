/** `backend/app/modules/alert/schemas.py`의 `AlertOut`과 1:1 대응. */
export interface Alert {
  id: number;
  asset_id: string;
  alert_type: string;
  severity: string;
  rule_version: string;
  evidence: Record<string, unknown>;
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  triggered_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}
