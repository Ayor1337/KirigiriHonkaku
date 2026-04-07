"""Add has_met_player to npc_state.

Revision ID: 20260407_0006
Revises: 20260406_0005
Create Date: 2026-04-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision: str = "20260407_0006"
down_revision: str | None = "20260406_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 NPC 状态添加是否已见过玩家的显式标记。"""

    with op.batch_alter_table("npc_state") as batch_op:
        batch_op.add_column(sa.Column("has_met_player", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """移除 NPC 是否已见过玩家标记。"""

    with op.batch_alter_table("npc_state") as batch_op:
        batch_op.drop_column("has_met_player")
