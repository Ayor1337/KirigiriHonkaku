"""step3 main loop keys

Revision ID: 20260403_0002
Revises: 20260402_0001
Create Date: 2026-04-03 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0002"
down_revision: str | None = "20260402_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """为 Step3 主循环补充稳定业务 key 字段。"""

    with op.batch_alter_table("location") as batch_op:
        batch_op.add_column(sa.Column("key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint("uq_location_map_key", ["map_id", "key"])

    with op.batch_alter_table("clue") as batch_op:
        batch_op.add_column(sa.Column("key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint("uq_clue_session_key", ["session_id", "key"])


def downgrade() -> None:
    """回滚 Step3 业务 key 字段。"""

    with op.batch_alter_table("clue") as batch_op:
        batch_op.drop_constraint("uq_clue_session_key", type_="unique")
        batch_op.drop_column("key")

    with op.batch_alter_table("location") as batch_op:
        batch_op.drop_constraint("uq_location_map_key", type_="unique")
        batch_op.drop_column("key")
