import { useState } from "react";
import { useApproveCommand, useCancelCommand, usePendingCommandsQuery } from "../../api/commands";
import { theme } from "../../styles/theme";

interface ApprovalQueueProps {
  selectedCommandId: string | null;
  onSelectCommand: (commandId: string) => void;
}

/**
 * 승인 대기열(`ApprovalQueue`). `docs/planning/01_프론트엔드_아키텍처.md` "안전한 명령
 * UX": 요청자와 승인자를 분리한다 — 요청자 본인이 승인자로 승인을 시도하면 백엔드가
 * 403으로 거부하고, 그 사유를 그대로 보여준다.
 */
export function ApprovalQueue({ selectedCommandId, onSelectCommand }: ApprovalQueueProps) {
  const { data: pending, isLoading } = usePendingCommandsQuery();
  const approve = useApproveCommand();
  const cancel = useCancelCommand();
  const [approvedBy, setApprovedBy] = useState("supervisor-1");

  return (
    <div style={{ padding: "0.5rem" }}>
      <strong>승인 대기열</strong>{" "}
      <span style={{ color: "gray" }}>({pending?.length ?? 0})</span>
      <div style={{ margin: "0.4rem 0" }}>
        <label style={{ fontSize: "0.85em", color: "gray" }}>
          승인자
          <input
            type="text"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            style={{ marginLeft: "0.4rem", width: "8rem" }}
          />
        </label>
      </div>

      {isLoading && <p style={{ color: "gray" }}>불러오는 중…</p>}
      {pending?.length === 0 && <p style={{ color: "gray" }}>승인 대기 중인 명령이 없습니다</p>}

      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {pending?.map((command) => (
          <li
            key={command.command_id}
            onClick={() => onSelectCommand(command.command_id)}
            style={{
              padding: "0.4rem",
              cursor: "pointer",
              // AssetList.tsx와 같은 버그(2026-10-12 스크린샷으로 발견) — 다크 테마에서
              // 밝은 배경+밝은 글자가 겹쳐 안 보이던 것을 같은 방식으로 고친다.
              background:
                selectedCommandId === command.command_id ? "rgba(34, 211, 238, 0.18)" : "transparent",
              fontSize: "0.9em",
              borderBottom: `1px solid ${theme.color.border.subtle}`,
            }}
          >
            <div>{command.command_id}</div>
            <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.25rem" }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  approve.mutate({ commandId: command.command_id, approvedBy });
                }}
              >
                승인
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  cancel.mutate({ commandId: command.command_id, cancelledBy: approvedBy });
                }}
              >
                취소
              </button>
            </div>
          </li>
        ))}
      </ul>
      {approve.isError && <p style={{ color: "crimson", fontSize: "0.85em" }}>{approve.error.message}</p>}
    </div>
  );
}
