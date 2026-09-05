/**
 * WebSocket 전용 store (스텁).
 *
 * 4단계(`docs/roadmap/04_단계_2D실시간관제_Day0810.md`)에서 `/ws/operations`
 * 구독, 재연결, stale 상태 표시를 구현한다. 장기 이력을 브라우저에 계속
 * 누적하지 않고 최신 상태와 짧은 차트 버퍼만 유지한다.
 */
export function useTelemetryStream() {
  // TODO: WebSocket 연결, 최신 프레임 store, 재연결 로직
  return { connected: false };
}
