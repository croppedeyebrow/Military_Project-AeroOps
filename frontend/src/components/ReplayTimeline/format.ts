import type { OperationSession } from "../../types/replay";

export interface ReplayRange {
  startMs: number;
  endMs: number;
}

/**
 * 운용 세션 → 재생 구간(ms, epoch).
 *
 * 목적: 세션을 고르면 재생 커서가 움직일 범위가 정해져야 한다(`useReplayStore.selectSession`).
 * 근거:
 * - 아직 진행 중인 세션(`ended_at === null` — 지금 떠 있는 백엔드 프로세스의 세션이
 *   대표적)은 끝 시각이 없다. "지금"(`nowMs`)을 끝으로 잡아 "시작부터 지금까지"를
 *   재생한다 — `api/replay.ts`의 `useReplayDatasetQuery`도 같은 규칙으로 이력을 받아온다.
 * - 시작과 끝이 같거나 뒤집힌 세션(곧바로 종료된 테스트 세션 등)은 슬라이더 범위가
 *   0이 되어 재생이 무의미하다 — 최소 1초 폭을 보장해 UI가 깨지지 않게 한다.
 * `nowMs`를 인자로 받는 이유: `Date.now()`를 내부에서 부르면 테스트가 시간에 의존한다.
 */
export function sessionRange(session: OperationSession, nowMs: number): ReplayRange {
  const startMs = Date.parse(session.started_at);
  const rawEndMs = session.ended_at ? Date.parse(session.ended_at) : nowMs;
  return { startMs, endMs: Math.max(rawEndMs, startMs + 1_000) };
}

/** 밀리초 길이를 `mm:ss`(1시간 이상이면 `h:mm:ss`)로 — 음수는 0으로 본다. */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(seconds).padStart(2, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

/**
 * 컨트롤 바의 "경과 / 전체" 라벨(예: `01:23 / 20:00`).
 *
 * 근거: 운영자는 "세션 시작으로부터 얼마나 지난 시점인지"(상대 위치)와 "실제로 몇 시
 * 몇 분이었는지"(절대 시각) 둘 다 필요하다 — 절대 시각은 컴포넌트에서
 * `toLocaleTimeString`으로 따로 보여주고, 이 함수는 상대 위치만 담당한다.
 */
export function formatReplayClock(currentMs: number, range: ReplayRange): string {
  return `${formatDuration(currentMs - range.startMs)} / ${formatDuration(
    range.endMs - range.startMs
  )}`;
}
