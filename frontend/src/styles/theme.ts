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
 * disconnected(neutral)와 WS 연결의 disconnected(danger)를 일부러 다른 토큰으로
 * 분리했다 — 전자는 "그 기체 하나가 한동안 조용하다"는 일상적 상태고, 후자는 "내
 * 브라우저 연결 자체가 끊겼다"는 즉시 조치가 필요한 상태라 같은 색으로 묶으면 둘의
 * 심각도 차이가 사라진다.
 *
 * 다크 테마 전환(2026-10-12, 사용자 결정): 사용자가 참고 이미지로 준 군사 C2(지휘통제)
 * 콘솔 스타일 — 짙은 네이비 배경 + 네온 시안 포인트 — 을 그대로 따른다. 이 파일의 역할
 * 덕분에(위 "목적" 참고) 값만 바꾸면 되고, 이미 이 토큰을 참조하는 3곳(FRESHNESS_COLOR/
 * CONNECTION_COLOR/SEVERITY_COLOR)은 코드 변경 없이 자동으로 다크 테마 색을 쓰게 된다.
 * 상태색(success/warning/danger)은 어두운 배경에서도 충분히 밝게(채도·명도를 올려서)
 * 다시 골랐다 — 밝은 배경용 색(`seagreen`, `goldenrod`, `crimson` 계열)은 짙은 네이비
 * 위에서 칙칙하게 묻혀 보인다.
 */
export const theme = {
  color: {
    status: {
      success: "#4ade80", // 정상/연결됨/최신 — 밝은 네온 그린
      warning: "#fbbf24", // 주의/연결 중·재연결 중/WARNING 경보 — 호박색
      danger: "#f87171", // 위험/연결 끊김/CRITICAL 경보 — 밝은 레드
      neutral: "#64748b", // 관심 밖(기체 신선도만) — 어두운 배경에서도 읽히는 slate 톤
    },
    accent: "#22d3ee", // 네온 시안 — 선택 강조, 트레일 선, 탭 밑줄, 재생 커서
    text: {
      primary: "#e6edf3", // 짙은 배경 위 기본 텍스트
      secondary: "#94a3b8",
      muted: "#64748b", // status.neutral과 같은 slate 톤
    },
    border: {
      default: "#24374a",
      subtle: "#1b2938",
    },
    background: {
      page: "#0b1420", // 전체 배경 — 거의 검정에 가까운 네이비
      panel: "#101d2c", // 헤더·사이드패널 등 한 단계 밝은 패널 배경
      sunken: "#13202e", // Vehicle3DViewer 캔버스·차트 배경처럼 패널보다 더 가라앉은 영역
      badge: "#17293a",
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
