"""Allow session title to stay empty before bootstrap.

Revision ID: 20260406_0005
Revises: 20260405_0004
Create Date: 2026-04-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision: str = "20260406_0005"
down_revision: str | None = "20260405_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """允许 AGENT 在 bootstrap 后再回写会话标题。"""

    with op.batch_alter_table("session") as batch_op:
        batch_op.alter_column("title", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    """回滚为创建会话时必须填写标题。"""

    with op.batch_alter_table("session") as batch_op:
        batch_op.alter_column("title", existing_type=sa.String(length=255), nullable=False)
