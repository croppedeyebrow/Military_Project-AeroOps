"""7단계: operation_sessions 테이블.

목적: `deployments`/`event_log`는 3단계 보정에서 이미 만들었지만, "운용 구간이 시작될 때
현재 deployment_id를 고정해 묶어두는" 테이블이 아직 없었다. 이 마이그레이션이 그 테이블을
추가한다 — `docs/planning/03_데이터베이스_아키텍처.md`, `docs/roadmap/작업분해_2단계_8단계.md`
7단계 절 참고.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-10
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operation_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        # nullable=False(근거는 app/modules/deployment/models.py의 OperationSession
        # docstring 참고): 세션은 항상 특정 배포에 묶여야 한다는 정합성 규칙을 DB에서도 강제.
        sa.Column("deployment_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # 조회 패턴: "현재 진행 중인 세션이 있는지"(ended_at IS NULL)와 "이 배포로 시작된
    # 세션들"(deployment_id)을 자주 조회하므로 함께 인덱싱한다.
    op.create_index(
        "ix_operation_sessions_deployment_ended",
        "operation_sessions",
        ["deployment_id", "ended_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_operation_sessions_deployment_ended", table_name="operation_sessions")
    op.drop_table("operation_sessions")
