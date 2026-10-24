"""CommandEnvelope 계약 (시뮬레이터 측 구현).

`legacy-backend/app/schemas/command.py`와 동일한 계약을 독립적으로 구현한다(사유는
`docs/decisions/0002-telemetry-contract-duplication.md` — Telemetry에 적용한 것과 같은
결정을 Command에도 적용한다). 필드 정의는 `docs/api/command_envelope_dictionary.md` 참고.
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
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at은 issued_at보다 이후여야 한다")
        return self
