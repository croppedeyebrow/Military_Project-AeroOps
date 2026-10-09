import { useQuery } from "@tanstack/react-query";
import type { Geofence, Mission, MissionRoute } from "../types/mission";
import { apiRequest } from "./client";

export function useMissionsQuery() {
  return useQuery({
    queryKey: ["missions"],
    queryFn: () => apiRequest<Mission[]>("/missions"),
    staleTime: 10_000,
  });
}

export function useMissionRouteQuery(missionId: string | null) {
  return useQuery({
    queryKey: ["missions", missionId, "route"],
    queryFn: () => apiRequest<MissionRoute>(`/missions/${missionId}/route`),
    enabled: missionId !== null,
    retry: false, // 아직 경로가 없으면(404) 그냥 표시 안 함
  });
}

export function useGeofencesQuery() {
  return useQuery({
    queryKey: ["geofences"],
    queryFn: () => apiRequest<Geofence[]>("/geofences"),
    staleTime: 10_000,
  });
}

/** 진행 중(ACTIVE)인 임무들의 예정 경로를 한 번에 모아온다 — 지도에 점선으로 그리는 용도.
 * 개별 미션마다 훅을 따로 호출할 수 없어(hooks-in-a-loop 금지) 쿼리 함수 안에서
 * `Promise.all`로 합친다. 경로가 아직 없는(404) 미션은 조용히 건너뛴다.
 */
export function useActiveMissionRoutesQuery() {
  return useQuery({
    queryKey: ["missions", "active-routes"],
    queryFn: async () => {
      const missions = await apiRequest<Mission[]>("/missions");
      const active = missions.filter((m) => m.status === "ACTIVE");
      const routes = await Promise.all(
        active.map(async (mission) => {
          try {
            return await apiRequest<MissionRoute>(`/missions/${mission.id}/route`);
          } catch {
            return null;
          }
        })
      );
      return routes.filter((r): r is MissionRoute => r !== null);
    },
    staleTime: 10_000,
  });
}
