"""step6 content expansion clue discovery rule

Revision ID: 20260405_0004
Revises: 20260403_0003
Create Date: 2026-04-05 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260405_0004"
down_revision: str | None = "20260403_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """为 Step6 增加条件线索发现规则字段。"""

    with op.batch_alter_table("clue") as batch_op:
        batch_op.add_column(sa.Column("discovery_rule", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    """回滚 Step6 条件线索发现规则字段。"""

    with op.batch_alter_table("clue") as batch_op:
        batch_op.drop_column("discovery_rule")
