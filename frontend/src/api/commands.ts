import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { CommandDetail, CommandStatus } from "../types/command";
import { apiRequest } from "./client";

export interface CreateCommandInput {
  command_id: string;
  idempotency_key: string;
  target_asset_id: string;
  command_type: string;
  requested_by: string;
  issued_at: string;
  expires_at: string;
  payload?: Record<string, unknown>;
}

/** 승인 대기 명령 목록 — `ApprovalQueue`가 폴링한다(WS로는 아직 command 채널을 안 보냄,
 * `docs/dev_history/legacy/` 참고: command 채널은 기체 dispatch 전용이라 UI로 직접 안 보낸다). */
export function usePendingCommandsQuery() {
  return useQuery({
    queryKey: ["commands", "PENDING_APPROVAL"],
    queryFn: () => apiRequest<CommandStatus[]>("/commands?status=PENDING_APPROVAL"),
    refetchInterval: 3_000,
  });
}

/**
 * 선택 기체의 최근 명령 목록 — `Vehicle3DViewer`가 "이 자세 변화는 command #123 실행
 * 결과"처럼 자세와 명령을 연결해 보여줄 때 쓴다(6단계 완료 기준). 전체 이력이 아니라
 * 최근 배지 표시용이라 짧은 간격으로 폴링한다.
 */
export function useAssetCommandsQuery(assetId: string | null) {
  return useQuery({
    queryKey: ["commands", "by-asset", assetId],
    queryFn: () => apiRequest<CommandStatus[]>(`/commands?target_asset_id=${assetId}`),
    enabled: assetId !== null,
    refetchInterval: 3_000,
  });
}

export function useCommandDetailQuery(commandId: string | null) {
  return useQuery({
    queryKey: ["commands", commandId],
    queryFn: () => apiRequest<CommandDetail>(`/commands/${commandId}`),
    enabled: commandId !== null,
    refetchInterval: 3_000,
  });
}

export function useCreateCommand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCommandInput) =>
      apiRequest<CommandStatus & { is_new: boolean }>("/commands", { method: "POST", json: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["commands"] }),
  });
}

export function useApproveCommand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commandId, approvedBy }: { commandId: string; approvedBy: string }) =>
      apiRequest<CommandStatus>(`/commands/${commandId}/approve`, {
        method: "POST",
        json: { approved_by: approvedBy },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["commands"] }),
  });
}

export function useCancelCommand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      commandId,
      cancelledBy,
      reason,
    }: {
      commandId: string;
      cancelledBy: string;
      reason?: string;
    }) =>
      apiRequest<CommandStatus>(`/commands/${commandId}/cancel`, {
        method: "POST",
        json: { cancelled_by: cancelledBy, reason },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["commands"] }),
  });
}
