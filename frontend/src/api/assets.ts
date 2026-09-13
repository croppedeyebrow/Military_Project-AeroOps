import { useQuery } from "@tanstack/react-query";
import type { TelemetryFrame } from "../types/telemetry";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchAssetsLatest(): Promise<TelemetryFrame[]> {
  const res = await fetch(`${API_BASE_URL}/assets`);
  if (!res.ok) {
    throw new Error(`자산 목록 조회 실패: ${res.status}`);
  }
  return res.json();
}

/**
 * 초기 화면 페인트용 REST 조회. WebSocket이 연결되는 동안(또는 실패 시)에도 화면이
 * 비어있지 않게 한다 — `docs/planning/01_프론트엔드_아키텍처.md`: "TanStack Query로
 * 초기 자산 목록/최신 상태 조회, WS와 병행". WS 스냅샷이 도착하면 store가 최신값으로
 * 덮어쓴다.
 */
export function useAssetsLatestQuery() {
  return useQuery({
    queryKey: ["assets", "latest"],
    queryFn: fetchAssetsLatest,
    staleTime: 5_000,
    retry: 1,
  });
}
