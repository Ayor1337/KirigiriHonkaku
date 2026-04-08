"""add board item title and content.

Revision ID: 20260408_0008
Revises: 20260408_0007
Create Date: 2026-04-08 00:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_0008"
down_revision: str | None = "20260408_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


EMPTY_TITLE = sa.text("''")


def upgrade() -> None:
    """为侦探板卡片补充持久化标题与正文。"""

    with op.batch_alter_table("board_item") as batch_op:
        batch_op.add_column(sa.Column("title", sa.String(length=255), nullable=False, server_default=EMPTY_TITLE))
        batch_op.add_column(sa.Column("content", sa.Text(), nullable=True))


def downgrade() -> None:
    """回滚侦探板卡片标题与正文列。"""

    with op.batch_alter_table("board_item") as batch_op:
        batch_op.drop_column("content")
        batch_op.drop_column("title")
