import type { TelemetryFrame } from "../../types/telemetry";

/**
 * 시간순(오름차순)으로 정렬된 `frames`에서 "`targetTimeMs` 시점에 보여줘야 할 프레임"을
 * 찾는다 — 정확히 그 시각의 프레임이 있을 가능성은 거의 없으므로(다운샘플된 이력이라
 * 점 사이가 비어있다), "그 시각 이전 중 가장 최근 프레임"을 고른다.
 *
 * 근거: 재생은 "그 순간 기체가 어디 있었는가"를 보여주는 것이라, 미래 프레임을 미리
 * 보여주면(다음 점을 보간/예측) 거짓 정보가 된다. 반면 과거의 가장 최근 값을 그대로
 * 유지하는 건 실제 센서 갱신 주기가 있는 시스템의 자연스러운 동작과 같다(다음 텔레메트리가
 * 올 때까지 마지막 값을 유지) — `classifyFreshness`(`types/telemetry.ts`)가 STALE 판정에
 * 쓰는 것과 같은 원칙이다.
 *
 * `targetTimeMs`가 첫 프레임보다 이르면(아직 아무 데이터도 없던 시점) `null`을 반환한다
 * — 호출부가 "아직 이 기체는 안 보인다"로 처리할 수 있게 한다.
 *
 * 이분 탐색을 쓰는 이유: 재생 중에는 `requestAnimationFrame`마다(초당 수십 번) 선택된
 * 모든 기체에 대해 이 함수가 호출된다 — 프레임 수가 수백~수천 개일 수 있어(다운샘플
 * 후에도) 선형 탐색은 불필요하게 느리다.
 */
export function findFrameAtTime(
  frames: TelemetryFrame[],
  targetTimeMs: number
): TelemetryFrame | null {
  if (frames.length === 0) return null;

  let low = 0;
  let high = frames.length - 1;
  if (Date.parse(frames[low].event_time) > targetTimeMs) return null;

  // 불변식: frames[low].event_time <= targetTimeMs (항상 참이 되도록 유지).
  // "targetTimeMs보다 큰 첫 인덱스"를 찾는 표준 이분 탐색이 아니라, "targetTimeMs 이하인
  // 마지막 인덱스"를 직접 좁혀나간다 — 결과를 바로 쓸 수 있어 한 단계 덜 번거롭다.
  while (low < high) {
    const mid = Math.ceil((low + high) / 2);
    if (Date.parse(frames[mid].event_time) <= targetTimeMs) {
      low = mid;
    } else {
      high = mid - 1;
    }
  }
  return frames[low];
}
