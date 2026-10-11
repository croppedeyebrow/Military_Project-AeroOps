/**
 * 재생 "시계"를 한 틱 전진시키는 순수 계산 — `useReplayStore.tick()`과
 * `requestAnimationFrame` 루프(컴포넌트 쪽)에서 공유한다.
 *
 * 목적: `requestAnimationFrame`은 실제 경과 시간(실시간 ms)만 알려준다. 재생 배속
 * (0.5×/1×/2×)을 적용해 "재생 시간축에서 얼마나 전진했는지"로 바꾸고, 구간 끝에
 * 닿으면 자동으로 멈추는 로직이 필요하다 — 이 계산 자체는 DOM/타이머 없이도 완전히
 * 테스트할 수 있어 따로 뗀다(`attitude.ts`가 쿼터니언 수학을, `frameLookup.ts`가 탐색을
 * 뗀 것과 같은 이유).
 */
export interface ReplayClockTick {
  nextTimeMs: number;
  finished: boolean;
}

export function advanceReplayTime(
  currentTimeMs: number,
  elapsedRealMs: number,
  speed: number,
  rangeEndMs: number
): ReplayClockTick {
  const next = currentTimeMs + elapsedRealMs * speed;
  if (next >= rangeEndMs) {
    return { nextTimeMs: rangeEndMs, finished: true };
  }
  return { nextTimeMs: next, finished: false };
}
