/** 재연결 지수 백오프 지연 계산(순수 함수라 훅과 분리해 단위 테스트한다). */
export const BASE_BACKOFF_MS = 1_000;
export const MAX_BACKOFF_MS = 15_000;

export function computeBackoffDelayMs(
  attempt: number,
  baseMs: number = BASE_BACKOFF_MS,
  maxMs: number = MAX_BACKOFF_MS
): number {
  if (attempt <= 0) return 0;
  return Math.min(baseMs * 2 ** (attempt - 1), maxMs);
}
