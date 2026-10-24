/** `legacy-backend/app/modules/command/schemas.py`와 1:1 대응. */
export interface CommandStatus {
  command_id: string;
  status: string;
  updated_at: string;
}

export interface CommandEvent {
  event_no: number;
  event_type: string;
  occurred_at: string;
  actor: string | null;
  detail: Record<string, unknown> | null;
}

export interface CommandDetail {
  command_id: string;
  idempotency_key: string;
  target_asset_id: string;
  command_type: string;
  requested_by: string;
  approved_by: string | null;
  status: string;
  issued_at: string;
  expires_at: string;
  deployment_id: string | null;
  created_at: string;
  updated_at: string;
  events: CommandEvent[];
}
