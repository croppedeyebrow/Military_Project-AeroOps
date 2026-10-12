/**
 * SVG 없이 테스트 가능한 순수 좌표 변환 — "시간(ms)/값 -> 픽셀"을 계산하는 부분만
 * 떼어낸다. `attitude.ts`가 쿼터니언 수학을, `frameLookup.ts`가 이분 탐색을 뗀 것과
 * 같은 이유: 좌표 계산이 틀리면 그래프 전체가 틀어지는데, 그 버그를 SVG를 실제로
 * 렌더링해야만 찾을 수 있다면(이 프로젝트엔 React 컴포넌트 렌더 테스트가 없다 —
 * `Vehicle3DViewer` 때부터의 결정) 영영 테스트가 안 된다.
 */

export interface Extent {
  min: number;
  max: number;
}

/** `domain`의 값을 `[0, rangePx]` 픽셀로 선형 변환한다.
 *
 * `domain.min === domain.max`(값이 전부 같음 — 예: 배터리가 재생 구간 내내 100%)일 때
 * 0으로 나누는 대신 항상 범위의 가운데(`rangePx / 2`)를 반환한다 — "변화가 없다"는
 * 사실을 "변화가 없는 수평선"으로 그리는 게 맞고, NaN으로 그래프 전체가 깨지면 안 된다.
 */
export function scaleLinear(value: number, domain: Extent, rangePx: number): number {
  if (domain.max === domain.min) return rangePx / 2;
  const ratio = (value - domain.min) / (domain.max - domain.min);
  return ratio * rangePx;
}

/** 값 목록에서 y축 도메인을 구한다. 위아래로 10% 여백을 둔다 — 선이 차트 테두리에
 * 딱 붙어 잘려 보이는 것보다, 약간 여유를 두는 쪽이 읽기 편하다. 값이 하나뿐이거나
 * 전부 같으면(`extentWithPadding`의 0-나누기 방지와 같은 이유) 위아래로 고정폭 여백을
 * 준다. */
export function extentWithPadding(values: number[], fallbackPadding = 1): Extent {
  if (values.length === 0) return { min: 0, max: 1 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return { min: min - fallbackPadding, max: max + fallbackPadding };
  const pad = (max - min) * 0.1;
  return { min: min - pad, max: max + pad };
}

export interface ChartPoint {
  timeMs: number;
  value: number;
}

/**
 * `points`(시간순)를 SVG `<path>`의 `d` 속성 문자열로 바꾼다 — `"M x0,y0 L x1,y1 L ..."`.
 * y축은 화면 좌표계(아래가 +)이므로 값이 큰 점일수록 y가 작아지게(위로) 뒤집는다
 * — 그래프는 "값이 클수록 위"가 직관이지만 SVG는 그 반대라, 이 함수 호출부가 매번
 * 뒤집는 걸 잊지 않도록 여기서 한 번에 처리한다.
 */
export function buildLinePath(
  points: ChartPoint[],
  timeDomain: Extent,
  valueDomain: Extent,
  widthPx: number,
  heightPx: number
): string {
  if (points.length === 0) return "";
  return points
    .map((point, index) => {
      const x = scaleLinear(point.timeMs, timeDomain, widthPx);
      const y = heightPx - scaleLinear(point.value, valueDomain, heightPx);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
