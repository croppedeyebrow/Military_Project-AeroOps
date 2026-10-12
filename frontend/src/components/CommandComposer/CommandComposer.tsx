import { useState, type FormEvent } from "react";
import { useCreateCommand } from "../../api/commands";
import { useOperationsStore } from "../../store/useOperationsStore";
import { theme } from "../../styles/theme";

const DEFAULT_EXPIRY_MINUTES = 5;

function randomSuffix(): string {
  return Math.random().toString(16).slice(2, 10);
}

/**
 * 명령 타입별 파라미터 입력 필드 정의.
 *
 * 목적/근거: 백엔드 `command_type`은 자유 문자열이고 `payload`도 자유 형식 dict라서
 * (`docs/api/command_envelope_dictionary.md`: "구체적인 값 집합은 5단계에서 command
 * 모듈이 검증한다" — 실제로는 특별히 검증하지 않고 그대로 저장) 백엔드를 전혀 바꾸지
 * 않고 프론트에서 타입별 입력 폼만 추가하면 된다. "명령 수행을 디테일하게 지정"하고
 * 싶다는 요구(2026-10-12)에 맞춰, 그동안 파라미터가 아예 없던 RTL/LOITER/ARM/DISARM
 * 4종에 "이동(MOVE_TO)"·"고도 변경(SET_ALTITUDE)"·"속도 변경(SET_SPEED)" 3종을 더하고,
 * 선택한 타입에 맞는 입력 필드만 보여준다.
 *
 * 필드 하나당 `key`(payload에 들어갈 키), `label`, `step`(소수 입력 단위)을 정의해두면
 * 폼 렌더링과 payload 조립을 전부 이 설정에서 기계적으로 뽑아낼 수 있다 — 새 명령
 * 타입을 추가할 때 이 배열에 한 줄 추가하는 것으로 끝난다(렌더링 로직 수정 불필요).
 */
interface PayloadField {
  key: string;
  label: string;
  step?: number;
}

const COMMAND_TYPES: { value: string; label: string; fields: PayloadField[] }[] = [
  { value: "RTL", label: "RTL(귀환)", fields: [] },
  { value: "LOITER", label: "LOITER(선회 대기)", fields: [] },
  { value: "ARM", label: "ARM", fields: [] },
  { value: "DISARM", label: "DISARM", fields: [] },
  {
    value: "MOVE_TO",
    label: "이동(MOVE_TO)",
    fields: [
      { key: "target_latitude", label: "목표 위도", step: 0.0001 },
      { key: "target_longitude", label: "목표 경도", step: 0.0001 },
      { key: "target_altitude_m", label: "목표 고도(m)", step: 1 },
    ],
  },
  {
    value: "SET_ALTITUDE",
    label: "고도 변경(SET_ALTITUDE)",
    fields: [{ key: "target_altitude_m", label: "목표 고도(m)", step: 1 }],
  },
  {
    value: "SET_SPEED",
    label: "속도 변경(SET_SPEED)",
    fields: [{ key: "target_speed_mps", label: "목표 속도(m/s)", step: 0.5 }],
  },
];

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
  // 타입을 바꿔도 이미 입력해둔 값은 유지한다 — 키별로 모아두고, 제출 시 "지금 타입이
  // 요구하는 필드"만 골라 payload로 추려낸다(아래 handleSubmit).
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});

  const selectedCommand = COMMAND_TYPES.find((c) => c.value === commandType) ?? COMMAND_TYPES[0];

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!targetAssetId) return;

    const now = new Date();
    const suffix = randomSuffix();
    const payload: Record<string, unknown> = {};
    for (const field of selectedCommand.fields) {
      const raw = fieldValues[field.key];
      if (raw !== undefined && raw !== "") payload[field.key] = Number(raw);
    }

    createCommand.mutate({
      command_id: `cmd-${suffix}`,
      idempotency_key: `idem-${suffix}`,
      target_asset_id: targetAssetId,
      command_type: commandType,
      requested_by: requestedBy,
      issued_at: now.toISOString(),
      expires_at: new Date(now.getTime() + expiryMinutes * 60_000).toISOString(),
      ...(Object.keys(payload).length > 0 ? { payload } : {}),
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
        {COMMAND_TYPES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>

      {selectedCommand.fields.length > 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.25rem",
            padding: "0.4rem",
            background: theme.color.background.sunken,
            borderRadius: theme.radius.sm,
          }}
        >
          {selectedCommand.fields.map((field) => (
            <label key={field.key} style={{ fontSize: "0.85em", color: theme.color.text.secondary }}>
              {field.label}
              <input
                type="number"
                step={field.step ?? 1}
                required
                value={fieldValues[field.key] ?? ""}
                onChange={(e) =>
                  setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
                style={{ marginLeft: "0.5rem", width: "7rem" }}
              />
            </label>
          ))}
        </div>
      )}

      <input
        type="text"
        value={requestedBy}
        onChange={(e) => setRequestedBy(e.target.value)}
        placeholder="요청자"
      />
      <label style={{ fontSize: "0.85em", color: theme.color.text.secondary }}>
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
        <p style={{ color: theme.color.status.danger, fontSize: "0.85em" }}>
          {createCommand.error.message}
        </p>
      )}
      {createCommand.isSuccess && (
        <p style={{ color: theme.color.status.success, fontSize: "0.85em" }}>
          요청됨: {createCommand.data.command_id} ({createCommand.data.status})
        </p>
      )}
    </form>
  );
}
