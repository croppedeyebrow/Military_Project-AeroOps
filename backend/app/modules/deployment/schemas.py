"""Deployment/OperationSession API 요청·응답 모델.

목적: `Deployment`/`OperationSession`(models.py)을 그대로 API로 내보내지 않고 얇은 Pydantic
모델을 거치는 이유는, ORM 모델에 나중에 내부용 컬럼이 추가돼도(예: 감사용 필드) API 계약이
저절로 바뀌지 않게 막기 위함이다(계약 변경은 항상 명시적으로).
"""
from datetime import datetime

from pydantic import BaseModel


class DeploymentOut(BaseModel):
    id: str
    git_sha: str
    image_tag: str
    schema_version: str | None
    rule_version: str | None
    config_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StartOperationSessionRequest(BaseModel):
    # None 허용: 자동화된 세션 시작(예: 통합 테스트, 배포 스크립트)은 "운영자"가 없다.
    started_by: str | None = None


class OperationSessionOut(BaseModel):
    id: str
    deployment_id: str
    started_at: datetime
    ended_at: datetime | None
    started_by: str | None

    model_config = {"from_attributes": True}


class EventLogOut(BaseModel):
    """`EventLog` row 1건. `payload`는 채널마다 모양이 달라(`dict`) 강한 타입을 포기했다
    — 재생 화면은 `source_channel`로 분기해서 해석한다(API 계약은 "컨테이너"만 보장)."""

    id: int
    operation_session_id: str | None
    event_time: datetime
    stream_sequence: int
    source_channel: str
    event_type: str
    correlation_id: str | None
    deployment_id: str | None
    payload: dict | None

    model_config = {"from_attributes": True}
