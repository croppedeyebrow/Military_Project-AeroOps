import type { TelemetryFrame } from "./telemetry";

/** `legacy-backend/app/modules/deployment/schemas.py`의 `OperationSessionOut`과 1:1 대응.
 * `ReplayTimeline`의 세션 선택 목록(`GET /operation-sessions`)이 쓴다. */
export interface OperationSession {
  id: string;
  deployment_id: string;
  started_at: string;
  ended_at: string | null;
  started_by: string | null;
}

/**
 * 기체별 재생용 텔레메트리 이력 묶음 — `asset_id`를 키로, 시간순(오름차순) 프레임
 * 배열을 값으로 가진다.
 *
 * `event_log`(세션의 정규화 이벤트)와는 다른 데이터다 — event_log의 텔레메트리 payload엔
 * `asset_id`/`sequence_no`만 있고 위경도·자세가 없다(`legacy-backend/app/modules/telemetry/
 * consumer.py`가 event_log에 전체 프레임을 복제해 넣지 않기 때문— 원본 중복 저장을
 * 피하려는 설계). 그래서 지도·3D 재생에 필요한 실제 위치/자세는 반드시
 * `GET /assets/{id}/telemetry`로 따로 받아와야 한다. 이 타입이 그 결과를 담는다.
 */
export type ReplayDataset = Record<string, TelemetryFrame[]>;
