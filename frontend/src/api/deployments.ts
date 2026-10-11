import { useQuery } from "@tanstack/react-query";
import type { BuildInfo, Deployment } from "../types/deployment";
import { apiRequest } from "./client";

/** "지금 이 프로세스가 어떤 버전인지". DB 연결이 필요 없는 가벼운 endpoint라
 * 자주 폴링해도 부담이 없다 — 헤더에 상시 표시되는 `DeploymentBadge`의 기본 모드가 쓴다.
 * 재배포로 버전이 바뀌는 건 흔치 않은 일이라 30초 간격이면 충분하다(1초 폴링처럼 자주
 * 할 이유가 없다 — 다른 실시간 데이터는 WS가 맡고 있다). */
export function useBuildInfoQuery() {
  return useQuery({
    queryKey: ["build-info"],
    queryFn: () => apiRequest<BuildInfo>("/system/build-info"),
    refetchInterval: 30_000,
  });
}

/** 특정 배포 하나(과거 버전 포함)를 id로 조회한다 — 재생 화면이 "이 구간은 어느
 * 배포였나"를 보여줄 때 쓴다. 배포 레코드는 등록된 뒤 절대 바뀌지 않으므로
 * (`Deployment` 모델 설계) 한 번 받으면 다시 폴링할 필요가 없다. */
export function useDeploymentQuery(deploymentId: string | null) {
  return useQuery({
    queryKey: ["deployments", deploymentId],
    queryFn: () => apiRequest<Deployment>(`/deployments/${deploymentId}`),
    enabled: deploymentId !== null,
    staleTime: Infinity,
  });
}
