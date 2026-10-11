import { useQuery } from "@tanstack/react-query";
import type { TelemetryFrame } from "../types/telemetry";
import type { OperationSession, ReplayDataset } from "../types/replay";
import { apiRequest } from "./client";

/** 세션 선택 UI(`ReplayTimeline`)가 쓰는 운용 세션 목록 — 최근 시작 순. */
export function useOperationSessionsQuery() {
  return useQuery({
    queryKey: ["operation-sessions"],
    queryFn: () => apiRequest<OperationSession[]>("/operation-sessions"),
    staleTime: 10_000,
  });
}

/** 다운샘플 모드로 받은 이력 응답의 `items`만 필요하다 — 나머지 필드(limit/offset 등)는
 * 재생에서 의미가 없다(페이지네이션이 아니라 전체 구간을 받는 모드이므로). */
interface TelemetryHistoryResponse {
  items: TelemetryFrame[];
}

const MAX_POINTS_PER_ASSET = 300;

/**
 * 세션 하나를 재생하기 위한 기체별 텔레메트리 이력을 모두 받아와 `ReplayDataset`으로
 * 합친다.
 *
 * 목적/근거: `telemetry_frames` 테이블엔 아직 `operation_session_id` 컬럼이 없다
 * (7단계 재생 엔진은 `event_log`부터 먼저 연결했고, 원본 텔레메트리 테이블까지 세션
 * id를 넣는 건 더 큰 스키마 변경이라 지금 범위에 넣지 않았다). 대신 세션 구간
 * (`ReplayTimeline/format.ts`의 `sessionRange`가 계산한 것)을 실제 시각(event_time)
 * 범위로 써서 `GET /assets/{id}/telemetry`를 호출한다 — 세션 경계가 곧 실제 시간
 * 경계이므로 이 근사로 충분하다.
 *
 * `range`를 세션 객체가 아니라 계산된 값으로 받는 이유: 진행 중인 세션은 끝 시각이
 * "지금"인데, 이 훅과 재생 슬라이더가 각자 `Date.now()`를 부르면 두 구간이 미세하게
 * 어긋난다. 슬라이더(`useReplayStore`)에 들어간 바로 그 구간으로 데이터를 받아야
 * "슬라이더 끝 = 데이터 끝"이 보장된다.
 *
 * 기체 목록은 `GET /assets`(전체 기체)를 그대로 쓴다 — 이 세션에 실제로 관여한 기체만
 * 고르려면 `event_log`를 먼저 훑어야 하는데, MVP 규모(기체 10대)에서는 전체 기체를
 * 다 조회해도 요청 수가 작아 이득이 크지 않다(YAGNI). 각 기체의 구간 내 데이터가
 * 없으면(`items.length === 0`) 조용히 결과에서 뺀다 — `useActiveMissionRoutesQuery`
 * (`api/missions.ts`)가 경로 없는 미션을 거르는 것과 같은 패턴.
 */
export function useReplayDatasetQuery(
  sessionId: string | null,
  range: { startMs: number; endMs: number } | null
) {
  return useQuery({
    queryKey: ["replay-dataset", sessionId, range?.startMs, range?.endMs],
    queryFn: async (): Promise<ReplayDataset> => {
      const assets = await apiRequest<TelemetryFrame[]>("/assets");
      const start = new Date(range!.startMs).toISOString();
      const end = new Date(range!.endMs).toISOString();

      const histories = await Promise.all(
        assets.map(async (asset) => {
          const params = new URLSearchParams({
            start,
            end,
            max_points: String(MAX_POINTS_PER_ASSET),
          });
          const history = await apiRequest<TelemetryHistoryResponse>(
            `/assets/${asset.asset_id}/telemetry?${params.toString()}`
          );
          return [asset.asset_id, history.items] as const;
        })
      );

      return Object.fromEntries(histories.filter(([, items]) => items.length > 0));
    },
    enabled: sessionId !== null && range !== null,
    staleTime: Infinity, // 같은 구간의 이력은 다시 바뀌지 않는다(불변 원본).
  });
}
