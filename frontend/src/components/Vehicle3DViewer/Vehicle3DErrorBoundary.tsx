import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * `docs/planning/01_프론트엔드_아키텍처.md`: "3D 오류가 지도 관제를 중단시키지 않도록
 * 오류 경계를 둔다." WebGL 컨텍스트 생성 실패, three.js 렌더 중 예외 등을 여기서 막아
 * 나머지 화면(2D 지도·목록·명령 콘솔)은 정상 동작하게 한다.
 */
export class Vehicle3DErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }): void {
    console.error("Vehicle3DViewer 렌더 오류(2D 관제는 계속 동작):", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: "0.75rem", color: "#a33", fontSize: "0.85em" }}>
          3D 뷰어를 표시할 수 없습니다(2D 관제·명령 기능은 정상 동작합니다).
          <br />
          {this.state.error.message}
        </div>
      );
    }
    return this.props.children;
  }
}
