"""3단계 보정: commands, command_events, event_log, deployments 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`, `docs/roadmap/작업분해_2단계_8단계.md`
"3단계 보정".

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commands",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("idempotency_key", sa.String(), nullable=False, unique=True),
        sa.Column("target_asset_id", sa.String(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("command_type", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_asset_state_version", sa.Integer(), nullable=True),
        sa.Column("deployment_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_commands_target_status_expires",
        "commands",
        ["target_asset_id", "status", "expires_at"],
    )

    op.create_table(
        "command_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("command_id", sa.String(), sa.ForeignKey("commands.id"), nullable=False),
        sa.Column("event_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("detail", JSONB(), nullable=True),
        sa.UniqueConstraint(
            "command_id", "event_no", name="uq_command_events_command_event_no"
        ),
    )
    op.create_index(
        "ix_command_events_command_occurred",
        "command_events",
        ["command_id", "occurred_at", "event_no"],
    )

    op.create_table(
        "deployments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("git_sha", sa.String(), nullable=False),
        sa.Column("image_tag", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=True),
        sa.Column("rule_version", sa.String(), nullable=True),
        sa.Column("config_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "event_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operation_session_id", sa.String(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stream_sequence", sa.BigInteger(), nullable=False),
        sa.Column("source_channel", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("deployment_id", sa.String(), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_event_log_session_time_seq",
        "event_log",
        ["operation_session_id", "event_time", "stream_sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_log_session_time_seq", table_name="event_log")
    op.drop_table("event_log")
    op.drop_table("deployments")
    op.drop_index("ix_command_events_command_occurred", table_name="command_events")
    op.drop_table("command_events")
    op.drop_index("ix_commands_target_status_expires", table_name="commands")
    op.drop_table("commands")
