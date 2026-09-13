/** "3분 전" 같은 경과 시간 표시. 통신 단절 마커 라벨에 쓴다(순수 함수라 단위 테스트한다). */
export function formatElapsed(elapsedMs: number): string {
  if (elapsedMs < 0) return "방금 전";

  const seconds = Math.floor(elapsedMs / 1000);
  if (seconds < 60) return `${seconds}초 전`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;

  const hours = Math.floor(minutes / 60);
  return `${hours}시간 전`;
}
