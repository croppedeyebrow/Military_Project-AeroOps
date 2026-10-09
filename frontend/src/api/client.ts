export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** 공통 fetch 래퍼 — 실패 시 서버가 돌려준 `detail`을 에러 메시지로 쓴다. */
export async function apiRequest<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const { json, headers, ...rest } = init ?? {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: json !== undefined ? { "Content-Type": "application/json", ...headers } : headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : res.statusText;
    throw new Error(typeof detail === "string" ? detail : `요청 실패: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
