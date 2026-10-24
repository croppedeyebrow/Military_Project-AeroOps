"""4단계: sync_sessions 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`,
`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.String(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_last_sequence_no", sa.Integer(), nullable=False),
        sa.Column("server_last_sequence_no", sa.Integer(), nullable=True),
        sa.Column("sequence_gap_count", sa.Integer(), nullable=False),
        sa.Column("reported_last_processed_command_id", sa.String(), nullable=True),
        sa.Column("pending_command_ids", JSONB(), nullable=True),
        sa.Column("snapshot_reissued", sa.Boolean(), nullable=False),
        sa.Column("detail", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_sessions_asset_created", "sync_sessions", ["asset_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_sessions_asset_created", table_name="sync_sessions")
    op.drop_table("sync_sessions")
