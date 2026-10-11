import type { CSSProperties } from "react";
import { useOperationSessionsQuery } from "../../api/replay";
import { useReplayStore, type ReplaySpeed } from "../../store/useReplayStore";
import { formatReplayClock, sessionRange } from "./format";
import { useReplayClockLoop } from "./useReplayClockLoop";

const SPEEDS: ReplaySpeed[] = [0.5, 1, 2];

/**
 * 재생 컨트롤 바 — 세션 선택, 재생/일시정지, 배속(0.5×/1×/2×), 스크럽 슬라이더.
 * 7단계 완료 기준 "0.5×, 1×, 2× 재생이 가능하다"의 UI 쪽.
 *
 * 이 컴포넌트는 "조작"만 한다 — 상태는 전부 `useReplayStore`에 있고, 지도·3D·상세
 * 패널은 같은 store의 `currentTimeMs`를 각자 읽어 그린다. 그래서 슬라이더를 끌거나
 * 재생 중일 때 세 화면이 별도 동기화 코드 없이 같은 시각을 가리킨다(완료 기준 "같은
 * timestamp에서 세 시각화 값이 일치한다"를 구조로 보장하는 방식).
 *
 * `useReplayClockLoop`을 여기서 마운트하는 이유: 시계는 컨트롤 바가 화면에 있을
 * 때(= 재생 탭이 열려 있을 때)만 돌아야 한다 — 탭을 벗어나 이 컴포넌트가 언마운트되면
 * 루프도 같이 멈춘다.
 */
export function ReplayTimeline() {
  useReplayClockLoop();

  const { data: sessions, isLoading } = useOperationSessionsQuery();
  const selectedSessionId = useReplayStore((s) => s.selectedSessionId);
  const rangeStartMs = useReplayStore((s) => s.rangeStartMs);
  const rangeEndMs = useReplayStore((s) => s.rangeEndMs);
  const currentTimeMs = useReplayStore((s) => s.currentTimeMs);
  const isPlaying = useReplayStore((s) => s.isPlaying);
  const speed = useReplayStore((s) => s.speed);
  const selectSession = useReplayStore((s) => s.selectSession);
  const play = useReplayStore((s) => s.play);
  const pause = useReplayStore((s) => s.pause);
  const seek = useReplayStore((s) => s.seek);
  const setSpeed = useReplayStore((s) => s.setSpeed);

  const handleSelectSession = (sessionId: string): void => {
    const session = sessions?.find((s) => s.id === sessionId);
    if (!session) return;
    // 진행 중 세션의 "끝"은 선택한 순간의 지금으로 고정한다(`sessionRange` docstring).
    const { startMs, endMs } = sessionRange(session, Date.now());
    selectSession(session.id, startMs, endMs);
  };

  const hasRange = rangeStartMs !== null && rangeEndMs !== null && currentTimeMs !== null;

  return (
    <div style={barStyle}>
      <select
        value={selectedSessionId ?? ""}
        onChange={(event) => handleSelectSession(event.target.value)}
        disabled={isLoading}
        style={{ maxWidth: 320 }}
      >
        <option value="" disabled>
          {isLoading ? "세션 불러오는 중…" : "재생할 운용 세션 선택"}
        </option>
        {sessions?.map((session) => (
          <option key={session.id} value={session.id}>
            {new Date(session.started_at).toLocaleString()} · {session.id}
            {session.ended_at ? "" : " (진행 중)"}
          </option>
        ))}
      </select>

      <button onClick={isPlaying ? pause : play} disabled={!hasRange} style={{ minWidth: 72 }}>
        {isPlaying ? "일시정지" : "재생"}
      </button>

      <div style={{ display: "flex", gap: "0.25rem" }}>
        {SPEEDS.map((value) => (
          <button
            key={value}
            onClick={() => setSpeed(value)}
            disabled={!hasRange}
            style={{ fontWeight: value === speed ? "bold" : "normal" }}
          >
            {value}×
          </button>
        ))}
      </div>

      <input
        type="range"
        min={rangeStartMs ?? 0}
        max={rangeEndMs ?? 0}
        // 1초 단위 — 텔레메트리 기본 주기(1 Hz)보다 촘촘하게 끌어봐야 보이는 차이가 없다.
        step={1000}
        value={currentTimeMs ?? 0}
        onChange={(event) => seek(Number(event.target.value))}
        disabled={!hasRange}
        style={{ flex: 1 }}
        aria-label="재생 위치"
      />

      <span style={{ fontFamily: "monospace", whiteSpace: "nowrap" }}>
        {hasRange
          ? `${formatReplayClock(currentTimeMs, { startMs: rangeStartMs, endMs: rangeEndMs })} · ${new Date(
              currentTimeMs
            ).toLocaleTimeString()}`
          : "--:-- / --:--"}
      </span>
    </div>
  );
}

const barStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  padding: "0.5rem 1rem",
  borderBottom: "1px solid #ddd",
};
