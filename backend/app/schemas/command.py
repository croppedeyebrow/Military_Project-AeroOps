"""CommandEnvelope 데이터 계약.

`docs/planning/05_데이터엔지니어링_아키텍처.md`: "CommandEnvelope은 command_id,
idempotency_key, target_asset_id, command_type, payload, requested_by, approved_by,
issued_at, expires_at, expected_asset_state_version, deployment_id를 포함한다. Telemetry와
Command 스키마·토픽·보존 정책은 분리한다."

Telemetry(`app.schemas.telemetry.TelemetryFrame`)와 계약을 물리적으로 분리한다 — 필드
집합이 겹치지 않으므로, 한쪽 계약으로 다른 쪽 데이터를 검증하면 항상 실패한다(필수 필드
누락). 자세한 필드 정의는 `docs/api/command_envelope_dictionary.md` 참고.

상태 머신(`DRAFT → PENDING_APPROVAL → APPROVED → DISPATCHED → ACKNOWLEDGED → EXECUTING
→ SUCCEEDED/FAILED/TIMED_OUT/CANCELLED`)과 전이 검증은 `app.modules.command`(5단계에서
완성)가 담당한다. 이 계약은 "명령 하나의 불변 스펙"만 표현한다 — 상태 필드 자체는 여기 없고
`command_events`(3단계 보정에서 migration 추가)가 이력을 갖는다.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class CommandEnvelope(BaseModel):
    schema_version: int = 1

    command_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    target_asset_id: str = Field(min_length=1)
    command_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    requested_by: str = Field(min_length=1)
    approved_by: str | None = None

    issued_at: datetime
    expires_at: datetime

    expected_asset_state_version: int | None = Field(default=None, ge=0)
    deployment_id: str | None = None

    @field_validator(
        "command_id", "idempotency_key", "target_asset_id", "command_type", "requested_by"
    )
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백일 수 없다")
        return value

    @model_validator(mode="after")
    def expires_after_issued(self) -> "CommandEnvelope":
        """만료 시각은 발급 시각보다 뒤여야 한다 — 이미 만료된 명령은 애초에 생성되지 않는다."""
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at은 issued_at보다 이후여야 한다")
        return self
