"""Mission/Geofence API 요청/응답 모델.

좌표는 GeoJSON 관례([경도, 위도] 순서)를 따른다 — 프론트가 별도 변환 없이 그대로
MapLibre 소스 데이터로 쓸 수 있게 한다.
"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

ZONE_TYPES = ("MISSION", "CAUTION", "PROHIBITED")


class MissionCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    start_time: datetime | None = None
    end_time: datetime | None = None


class MissionUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None  # PLANNED | ACTIVE | COMPLETED | ABORTED
    start_time: datetime | None = None
    end_time: datetime | None = None


class MissionOut(BaseModel):
    id: str
    name: str
    status: str
    start_time: datetime | None
    end_time: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RouteSetRequest(BaseModel):
    """`waypoints`: `[[lon, lat, alt_m], ...]`, 최소 2개."""

    waypoints: list[list[float]]

    @field_validator("waypoints")
    @classmethod
    def must_have_at_least_two_points(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 2:
            raise ValueError("경로는 최소 2개 지점이 필요하다")
        for point in value:
            if len(point) != 3:
                raise ValueError("각 지점은 [lon, lat, alt_m] 3개 값이어야 한다")
        return value


class RouteOut(BaseModel):
    mission_id: str
    waypoints: list[list[float]]
    recorded_at: datetime

    model_config = {"from_attributes": True}


class GeofenceCreateRequest(BaseModel):
    """`polygon`: 닫힌 링 `[[lon, lat], ...]`(첫 점 == 마지막 점), 최소 4개 점."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    zone_type: str
    polygon: list[list[float]]

    @field_validator("zone_type")
    @classmethod
    def zone_type_must_be_known(cls, value: str) -> str:
        if value not in ZONE_TYPES:
            raise ValueError(f"zone_type은 {ZONE_TYPES} 중 하나여야 한다")
        return value

    @field_validator("polygon")
    @classmethod
    def polygon_must_be_closed_ring(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 4:
            raise ValueError("폴리곤은 최소 4개 점(닫힌 링)이 필요하다")
        if value[0] != value[-1]:
            raise ValueError("폴리곤의 첫 점과 마지막 점이 같아야 한다(닫힌 링)")
        for point in value:
            if len(point) != 2:
                raise ValueError("각 점은 [lon, lat] 2개 값이어야 한다")
        return value


class GeofenceOut(BaseModel):
    id: str
    name: str
    zone_type: str
    polygon: list[list[float]]
    created_at: datetime

    model_config = {"from_attributes": True}
