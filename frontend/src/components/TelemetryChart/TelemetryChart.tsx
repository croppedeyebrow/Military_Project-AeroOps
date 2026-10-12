import { useState } from "react";
import { useReplayStore } from "../../store/useReplayStore";
import { theme } from "../../styles/theme";
import type { ReplayDataset } from "../../types/replay";
import type { TelemetryFrame } from "../../types/telemetry";
import { buildLinePath, extentWithPadding, scaleLinear, type ChartPoint } from "./scale";

interface Props {
  dataset: ReplayDataset;
}

type FieldKey = "battery_pct" | "altitude_m" | "speed_mps";

const FIELDS: { key: FieldKey; label: string }[] = [
  { key: "battery_pct", label: "배터리(%)" },
  { key: "altitude_m", label: "고도(m)" },
  { key: "speed_mps", label: "속도(m/s)" },
];

const WIDTH = 760;
const HEIGHT = 120;
const PADDING = { top: 8, right: 12, bottom: 8, left: 12 };

/**
 * 선택 기체의 시계열 값(배터리/고도/속도)을 재생 구간 전체에 대해 선 그래프로 보여주고,
 * 재생 커서(현재 재생 시각)를 수직선으로 함께 그린다.
 *
 * `ReplayMap`/`ReplayVehicle3DViewer`/`ReplayAssetDetail`과 같은 패턴 — "지금 커서가
 * 몇 시인지"는 `useReplayStore`에서, "이 세션의 전체 이력"은 `dataset` prop으로 받는다.
 * 다만 지도/3D/상세는 "그 순간 하나의 프레임"만 보면 되는데, 이 차트는 "구간 전체의
 * 모든 점"이 한 번에 필요하다는 점이 다르다 — 그래서 `findFrameAtTime` 대신 선택된
 * 기체의 프레임 배열 전체를 그대로 쓴다.
 */
export function TelemetryChart({ dataset }: Props) {
  const [field, setField] = useState<FieldKey>("battery_pct");
  const selectedAssetId = useReplayStore((s) => s.selectedAssetId);
  const rangeStartMs = useReplayStore((s) => s.rangeStartMs);
  const rangeEndMs = useReplayStore((s) => s.rangeEndMs);
  const currentTimeMs = useReplayStore((s) => s.currentTimeMs);

  const frames = selectedAssetId ? dataset[selectedAssetId] : undefined;

  if (!selectedAssetId) {
    return <Notice>지도 또는 목록에서 기체를 선택하면 시계열 차트를 표시합니다.</Notice>;
  }
  if (!frames || frames.length === 0 || rangeStartMs === null || rangeEndMs === null) {
    return <Notice>이 기체의 재생 구간 데이터가 없습니다.</Notice>;
  }

  const innerWidth = WIDTH - PADDING.left - PADDING.right;
  const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;
  const timeDomain = { min: rangeStartMs, max: rangeEndMs };

  // null인 값(해당 필드가 아직 안 보고된 프레임)은 선을 끊지 않고 그냥 건너뛴다 —
  // 값이 0인 것처럼 그리면(null -> 0으로 바꾸면) 실제 배터리 0%와 "값 없음"을
  // 구분할 수 없게 되는 더 나쁜 오류다.
  const points: ChartPoint[] = frames
    .filter((frame): frame is TelemetryFrame & { [K in FieldKey]: number } => frame[field] !== null)
    .map((frame) => ({ timeMs: Date.parse(frame.event_time), value: frame[field] }));

  const valueDomain = extentWithPadding(points.map((p) => p.value));
  const path = buildLinePath(points, timeDomain, valueDomain, innerWidth, innerHeight);
  const cursorX =
    currentTimeMs !== null ? scaleLinear(currentTimeMs, timeDomain, innerWidth) : null;

  return (
    // 버그 수정(2026-10-12, 스크린샷 리뷰로 발견한 계열): border/선 색이 다크 테마
    // 전환 전 밝은 배경 기준 값(#ddd, #3388ff) 그대로 남아있었다. 토큰으로 교체.
    <div style={{ padding: "0.5rem 1rem", borderBottom: `1px solid ${theme.color.border.subtle}` }}>
      <div style={{ display: "flex", gap: "0.25rem", marginBottom: "0.25rem" }}>
        {FIELDS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setField(key)}
            style={{ fontWeight: key === field ? "bold" : "normal", fontSize: "0.8rem" }}
          >
            {label}
          </button>
        ))}
      </div>
      {points.length === 0 ? (
        <Notice>이 필드는 이 기체에서 보고된 값이 없습니다.</Notice>
      ) : (
        <svg width="100%" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ display: "block" }}>
          <g transform={`translate(${PADDING.left}, ${PADDING.top})`}>
            <path d={path} fill="none" stroke={theme.color.accent} strokeWidth={1.5} />
            {cursorX !== null && (
              <line
                x1={cursorX}
                x2={cursorX}
                y1={0}
                y2={innerHeight}
                // 데이터 선(accent, 시안)과 뚜렷이 구분되게 warning(amber) 톤을 쓴다.
                stroke={theme.color.status.warning}
                strokeWidth={1}
              />
            )}
          </g>
        </svg>
      )}
    </div>
  );
}

function Notice({ children }: { children: string }) {
  return <div style={{ padding: "0.5rem 1rem", color: "gray", fontSize: "0.85rem" }}>{children}</div>;
}
