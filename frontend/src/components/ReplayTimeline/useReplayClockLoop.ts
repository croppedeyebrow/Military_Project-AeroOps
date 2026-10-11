import { useEffect, useRef } from "react";
import { useReplayStore } from "../../store/useReplayStore";

/**
 * 재생 중일 때만 `requestAnimationFrame` 루프를 돌려 `useReplayStore.tick()`을
 * 호출한다.
 *
 * 근거: 매 프레임마다 "지금이 몇 시인지 계산"하는 로직(`advanceReplayTime`)은 이미
 * 순수 함수로 분리했다 — 이 훅의 책임은 그 계산에 넘길 "실제 경과 시간(ms)"을
 * `requestAnimationFrame`에서 재는 것뿐이다. `isPlaying`이 false면 루프 자체를 돌리지
 * 않는다(배터리/CPU를 불필요하게 쓰지 않는다 — 일시정지 중엔 할 일이 없다).
 *
 * `ReplayTimeline`이 마운트돼 있을 때만 이 훅을 쓰므로, 재생 탭을 벗어나면(언마운트)
 * 자동으로 루프도 멈춘다 — 별도의 "탭이 꺼졌으니 멈춰라" 신호가 필요 없다.
 */
export function useReplayClockLoop(): void {
  const isPlaying = useReplayStore((s) => s.isPlaying);
  const tick = useReplayStore((s) => s.tick);
  const lastTimestampRef = useRef<number | null>(null);
  const frameIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      lastTimestampRef.current = null;
      return;
    }

    const step = (timestamp: number): void => {
      if (lastTimestampRef.current !== null) {
        tick(timestamp - lastTimestampRef.current);
      }
      lastTimestampRef.current = timestamp;
      frameIdRef.current = requestAnimationFrame(step);
    };
    frameIdRef.current = requestAnimationFrame(step);

    return () => {
      if (frameIdRef.current !== null) cancelAnimationFrame(frameIdRef.current);
      lastTimestampRef.current = null;
    };
  }, [isPlaying, tick]);
}
