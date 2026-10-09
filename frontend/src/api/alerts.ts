import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";

/** 경보 확인/해제 — 성공하면 store의 실시간 상태(WS로 이미 반영됨)와 어긋나지 않도록
 * 별도 캐시 무효화는 하지 않는다. 확인/해제 결과 자체는 이 mutation의 반환값으로 바로
 * 화면에 반영하고, 최종 진실은 다음 WS 갱신(추가하지 않았다면 이 응답)이 맡는다.
 */
export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, acknowledgedBy }: { alertId: number; acknowledgedBy: string }) =>
      apiRequest(`/alerts/${alertId}/acknowledge`, { method: "POST", json: { acknowledged_by: acknowledgedBy } }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["audit-logs"] }),
  });
}

export function useResolveAlert() {
  return useMutation({
    mutationFn: ({ alertId, resolvedBy }: { alertId: number; resolvedBy: string }) =>
      apiRequest(`/alerts/${alertId}/resolve`, { method: "POST", json: { resolved_by: resolvedBy } }),
  });
}
