import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: string;
  env?: string;
}

async function fetchHealth(path: "/health/live" | "/health/ready"): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

/** 1단계 완료 기준: 프론트에서 백엔드 health 결과를 확인한다. */
export function useBackendHealth() {
  return useQuery({
    queryKey: ["health", "ready"],
    queryFn: () => fetchHealth("/health/ready"),
    retry: 1,
  });
}
