import { useBackendHealth } from "./api/health";

/**
 * 1단계(프로젝트 기반) 임시 화면.
 * 백엔드 health 상태를 확인하는 용도이며, 4단계부터
 * OperationsMap 등 실제 관제 화면으로 대체된다.
 */
function App() {
  const { data, isLoading, isError, error } = useBackendHealth();

  return (
    <main style={{ padding: "2rem", fontFamily: "system-ui" }}>
      <h1>AeroOps 관제 플랫폼</h1>
      <p>1단계 — 프로젝트 기반: 백엔드 연결 확인</p>

      {isLoading && <p>백엔드 상태 확인 중...</p>}
      {isError && (
        <p style={{ color: "crimson" }}>
          백엔드에 연결할 수 없습니다: {(error as Error).message}
        </p>
      )}
      {data && (
        <p style={{ color: "seagreen" }}>
          백엔드 상태: {data.status} (env: {data.env ?? "unknown"})
        </p>
      )}
    </main>
  );
}

export default App;
