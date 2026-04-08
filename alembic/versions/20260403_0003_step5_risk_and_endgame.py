"""step5 risk and endgame foundation

Revision ID: 20260403_0003
Revises: 20260403_0002
Create Date: 2026-04-03 00:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0003"
down_revision: str | None = "20260403_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """为 Step5 增加 truth payload 事实源。"""

    with op.batch_alter_table("session") as batch_op:
        batch_op.add_column(sa.Column("truth_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    """回滚 Step5 truth payload 字段。"""

    with op.batch_alter_table("session") as batch_op:
        batch_op.drop_column("truth_payload")
