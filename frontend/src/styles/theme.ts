/**
 * 디자인 토큰 — 색상·간격·타이포그래피 기준값을 한 곳에 모은다.
 *
 * 목적: 지금까지는 거의 모든 컴포넌트가 인라인 `style={{...}}`에 색상·여백을 직접
 * 문자열로 박아넣었다. 조사해보니 "같은 의미"인데 다른 표현을 쓰는 경우가 많았다 —
 * 예를 들어 "정상" 상태를 `FRESHNESS_COLOR.live`는 `#2e8b57`로, `CONNECTION_COLOR.connected`
 * 는 named color `"seagreen"`으로 각각 따로 적어놔서, 둘이 실제로 같은 색인지 코드만
 * 보고는 알기 어려웠다. 간격도 `0.4rem`/`0.5rem`/`0.25rem`이 뚜렷한 기준 없이 섞여
 * 있었다. 이 파일은 "React 인라인 스타일 패턴 자체를 CSS-in-JS 라이브러리나 Tailwind로
 * 바꾸는" 큰 작업이 아니라, 지금 쓰는 패턴을 유지하면서 값만 한 곳에서 가져오게 하는
 * 최소 변경이다 — 새 빌드 의존성이 없고, 기존 컴포넌트를 점진적으로(이 다음 단위들에서)
 * 옮겨갈 수 있다.
 *
 * 왜 상태 색상을 success/warning/danger/neutral 4가지로만 나눴는지: 지금 코드에 있는
 * 모든 상태 표시(WS 연결, 기체 신선도, 경보 심각도)가 실제로는 "좋음/주의/나쁨" 3단계
 * +"관심 밖(연결이 그냥 오래돼서 조용해짐, 에러는 아님)" 1단계로 환원된다. 기체 신선도의
 * disconnected(회색, neutral)와 WS 연결의 disconnected(빨강, danger)를 일부러 다른
 * 토큰으로 분리했다 — 전자는 "그 기체 하나가 한동안 조용하다"는 일상적 상태고, 후자는
 * "내 브라우저 연결 자체가 끊겼다"는 즉시 조치가 필요한 상태라 같은 색으로 묶으면
 * 둘의 심각도 차이가 사라진다.
 */
export const theme = {
  color: {
    status: {
      success: "#2e8b57", // 정상/연결됨/최신 — FRESHNESS_COLOR.live, CONNECTION_COLOR.connected
      warning: "#daa520", // 주의/연결 중·재연결 중/WARNING 경보 — goldenrod
      danger: "#dc143c", // 위험/연결 끊김/CRITICAL 경보 — crimson
      neutral: "#808080", // 관심 밖(기체 신선도만 — 통신 단절은 일상적일 수 있어 danger와 분리)
    },
    accent: "#3388ff", // 선택 강조, 트레일 선, 탭 밑줄 등 — 기존 OperationsMap 트레일 색 그대로
    text: {
      primary: "#1a1a1a",
      secondary: "#555555",
      muted: "#808080", // status.neutral과 같은 회색이지만 "텍스트 색"이라는 의도로 별도 키 유지
    },
    border: {
      default: "#dddddd",
      subtle: "#eeeeee",
    },
    background: {
      page: "#ffffff",
      sunken: "#f4f4f4", // Vehicle3DViewer 캔버스 배경(#f2f2f2)과 거의 같은 계열 — 패널 배경에도 재사용
      badge: "#eeeeee",
    },
  },
  space: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "0.75rem",
    lg: "1rem",
    xl: "1.5rem",
  },
  fontSize: {
    xs: "0.8rem",
    sm: "0.85rem",
    base: "0.95rem",
    lg: "1.1rem", // 헤더(h1) 수준
  },
  radius: {
    sm: "4px",
    full: "50%",
  },
} as const;
