import { useState, type FormEvent } from "react";
import { useCreateCommand } from "../../api/commands";
import { useOperationsStore } from "../../store/useOperationsStore";

const DEFAULT_EXPIRY_MINUTES = 5;

function randomSuffix(): string {
  return Math.random().toString(16).slice(2, 10);
}

/**
 * 명령 요청 생성 폼(`CommandComposer`).
 * `docs/planning/01_프론트엔드_아키텍처.md` "안전한 명령 UX": 명령 생성과 승인을 서로
 * 다른 사용자 행동으로 구분한다 — 여기서는 생성만 하고, 승인은 `ApprovalQueue`가 맡는다.
 */
export function CommandComposer() {
  const assetIds = useOperationsStore((s) => Object.keys(s.assetsById));
  const createCommand = useCreateCommand();

  const [targetAssetId, setTargetAssetId] = useState("");
  const [commandType, setCommandType] = useState("RTL");
  const [requestedBy, setRequestedBy] = useState("operator-1");
  const [expiryMinutes, setExpiryMinutes] = useState(DEFAULT_EXPIRY_MINUTES);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!targetAssetId) return;

    const now = new Date();
    const suffix = randomSuffix();
    createCommand.mutate({
      command_id: `cmd-${suffix}`,
      idempotency_key: `idem-${suffix}`,
      target_asset_id: targetAssetId,
      command_type: commandType,
      requested_by: requestedBy,
      issued_at: now.toISOString(),
      expires_at: new Date(now.getTime() + expiryMinutes * 60_000).toISOString(),
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{ display: "flex", flexDirection: "column", gap: "0.4rem", padding: "0.5rem" }}
    >
      <strong>명령 요청</strong>
      <select value={targetAssetId} onChange={(e) => setTargetAssetId(e.target.value)} required>
        <option value="">대상 기체 선택</option>
        {assetIds.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
      <select value={commandType} onChange={(e) => setCommandType(e.target.value)}>
        <option value="RTL">RTL(귀환)</option>
        <option value="LOITER">LOITER(선회 대기)</option>
        <option value="ARM">ARM</option>
        <option value="DISARM">DISARM</option>
      </select>
      <input
        type="text"
        value={requestedBy}
        onChange={(e) => setRequestedBy(e.target.value)}
        placeholder="요청자"
      />
      <label style={{ fontSize: "0.85em", color: "gray" }}>
        만료(분)
        <input
          type="number"
          min={1}
          value={expiryMinutes}
          onChange={(e) => setExpiryMinutes(Number(e.target.value))}
          style={{ marginLeft: "0.5rem", width: "4rem" }}
        />
      </label>
      <button type="submit" disabled={!targetAssetId || createCommand.isPending}>
        {createCommand.isPending ? "요청 중…" : "명령 요청"}
      </button>
      {createCommand.isError && (
        <p style={{ color: "crimson", fontSize: "0.85em" }}>{createCommand.error.message}</p>
      )}
      {createCommand.isSuccess && (
        <p style={{ color: "seagreen", fontSize: "0.85em" }}>
          요청됨: {createCommand.data.command_id} ({createCommand.data.status})
        </p>
      )}
    </form>
  );
}
