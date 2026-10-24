"""3단계: assets, telemetry_frames, asset_latest_state 초기 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`, `docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`.

Revision ID: 0001
Revises:
Create Date: 2026-09-06
"""
import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("asset_type", sa.String(), nullable=False, server_default="drone"),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "telemetry_frames",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("mission_id", sa.String(), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Float(), nullable=False),
        sa.Column("position", Geometry("POINTZ", srid=4326), nullable=True),
        sa.Column("speed_mps", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("roll_deg", sa.Float(), nullable=True),
        sa.Column("pitch_deg", sa.Float(), nullable=True),
        sa.Column("yaw_deg", sa.Float(), nullable=True),
        sa.Column("battery_pct", sa.Float(), nullable=False),
        sa.Column("rssi_dbm", sa.Float(), nullable=True),
        sa.Column("flight_mode", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "sequence_no", name="uq_telemetry_asset_sequence"),
    )
    op.create_index(
        "ix_telemetry_asset_event_time",
        "telemetry_frames",
        ["asset_id", sa.text("event_time DESC")],
    )
    op.create_index(
        "ix_telemetry_position", "telemetry_frames", ["position"], postgresql_using="gist"
    )

    op.create_table(
        "asset_latest_state",
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("mission_id", sa.String(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Float(), nullable=False),
        sa.Column("position", Geometry("POINTZ", srid=4326), nullable=True),
        sa.Column("speed_mps", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("roll_deg", sa.Float(), nullable=True),
        sa.Column("pitch_deg", sa.Float(), nullable=True),
        sa.Column("yaw_deg", sa.Float(), nullable=True),
        sa.Column("battery_pct", sa.Float(), nullable=False),
        sa.Column("rssi_dbm", sa.Float(), nullable=True),
        sa.Column("flight_mode", sa.String(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_latest_state")
    op.drop_index("ix_telemetry_position", table_name="telemetry_frames")
    op.drop_index("ix_telemetry_asset_event_time", table_name="telemetry_frames")
    op.drop_table("telemetry_frames")
    op.drop_table("assets")
