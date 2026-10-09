"""5단계: missions, mission_routes, geofences, alerts, audit_logs 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`,
`docs/roadmap/05_단계_임무경보관리_Day11-13.md`.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PLANNED"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "mission_routes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("mission_id", sa.String(), sa.ForeignKey("missions.id"), nullable=False),
        sa.Column("waypoints", JSONB(), nullable=False),
        sa.Column("route", Geometry("LINESTRINGZ", srid=4326), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "geofences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("zone_type", sa.String(), nullable=False),
        sa.Column("polygon", JSONB(), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("alert_type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.Column(
            "evidence", JSONB(), nullable=False
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_asset_status", "alerts", ["asset_id", "status"])
    op.create_index(
        "ix_alerts_open", "alerts", ["asset_id"], postgresql_where=sa.text("status = 'OPEN'")
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False, server_default="SUCCESS"),
        sa.Column(
            "detail", JSONB(), nullable=True
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_audit_logs_target", "audit_logs", ["target_type", "target_id", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_alerts_open", table_name="alerts")
    op.drop_index("ix_alerts_asset_status", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("geofences")
    op.drop_table("mission_routes")
    op.drop_table("missions")
