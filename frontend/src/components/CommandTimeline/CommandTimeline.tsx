import { useCommandDetailQuery } from "../../api/commands";
import { theme } from "../../styles/theme";

const EVENT_LABEL: Record<string, string> = {
  CREATED: "생성됨",
  APPROVED: "승인됨",
  DISPATCHED: "전달됨",
  ACKNOWLEDGED: "기체 ACK",
  EXECUTING: "실행 중",
  SUCCEEDED: "성공",
  FAILED: "실패",
  TIMED_OUT: "시간 초과",
  CANCELLED: "취소됨",
};

/** 명령 상태 타임라인(`CommandTimeline`). `ApprovalQueue`에서 고른 명령의 이력을 보여준다. */
export function CommandTimeline({ commandId }: { commandId: string | null }) {
  const { data: detail, isLoading } = useCommandDetailQuery(commandId);

  if (!commandId) {
    return <div style={{ padding: "0.5rem", color: "gray" }}>명령을 선택하세요.</div>;
  }
  if (isLoading || !detail) {
    return <div style={{ padding: "0.5rem", color: "gray" }}>불러오는 중…</div>;
  }

  return (
    <div style={{ padding: "0.5rem" }}>
      <strong>{detail.command_id}</strong>
      <div style={{ color: "gray", fontSize: "0.85em" }}>
        {detail.command_type} → {detail.target_asset_id} · 현재 상태: {detail.status}
      </div>
      <ol style={{ listStyle: "none", margin: "0.5rem 0 0", padding: 0 }}>
        {detail.events.map((event) => (
          <li
            key={event.event_no}
            style={{
              borderLeft: `2px solid ${theme.color.border.default}`,
              paddingLeft: "0.6rem",
              marginBottom: "0.4rem",
              fontSize: "0.85em",
            }}
          >
            <div>
              <strong>{EVENT_LABEL[event.event_type] ?? event.event_type}</strong>{" "}
              <span style={{ color: "gray" }}>#{event.event_no}</span>
            </div>
            <div style={{ color: "gray" }}>
              {new Date(event.occurred_at).toLocaleString()} · {event.actor ?? "system"}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
