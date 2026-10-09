/** `backend/app/modules/mission/schemas.py`와 1:1 대응. */
export interface Mission {
  id: string;
  name: string;
  status: string;
  start_time: string | null;
  end_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface MissionRoute {
  mission_id: string;
  /** `[[lon, lat, alt_m], ...]` */
  waypoints: number[][];
  recorded_at: string;
}

export interface Geofence {
  id: string;
  name: string;
  zone_type: "MISSION" | "CAUTION" | "PROHIBITED";
  /** 닫힌 링 `[[lon, lat], ...]` */
  polygon: number[][];
  created_at: string;
}
