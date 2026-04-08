"""move runtime text artifacts into database.

Revision ID: 20260408_0007
Revises: 20260407_0006
Create Date: 2026-04-08 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_0007"
down_revision: str | None = "20260407_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


EMPTY_OBJECT = sa.text("'{}'")
EMPTY_ARRAY = sa.text("'[]'")


def upgrade() -> None:
    """把运行时文本产物从文件路径迁移到数据库列。"""

    with op.batch_alter_table("session") as batch_op:
        batch_op.add_column(sa.Column("story_markdown", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("history_markdown", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("truth_markdown", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("latest_action_payload", sa.JSON(), nullable=False, server_default=EMPTY_OBJECT))
        batch_op.add_column(sa.Column("ai_generation_log_entries", sa.JSON(), nullable=False, server_default=EMPTY_ARRAY))
        batch_op.drop_column("story_file_path")
        batch_op.drop_column("history_file_path")
        batch_op.drop_column("truth_file_path")

    with op.batch_alter_table("npc") as batch_op:
        batch_op.add_column(sa.Column("profile_markdown", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("memory_markdown", sa.Text(), nullable=True))
        batch_op.drop_column("profile_file_path")
        batch_op.drop_column("memory_file_path")

    with op.batch_alter_table("clue") as batch_op:
        batch_op.add_column(sa.Column("document_markdown", sa.Text(), nullable=True))
        batch_op.drop_column("document_file_path")

    with op.batch_alter_table("dialogue") as batch_op:
        batch_op.add_column(sa.Column("summary_markdown", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("transcript_markdown", sa.Text(), nullable=True))
        batch_op.drop_column("summary_file_path")
        batch_op.drop_column("transcript_file_path")


def downgrade() -> None:
    """回滚文本入库迁移，恢复旧的文件路径列。"""

    with op.batch_alter_table("dialogue") as batch_op:
        batch_op.add_column(sa.Column("summary_file_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("transcript_file_path", sa.Text(), nullable=True))
        batch_op.drop_column("summary_markdown")
        batch_op.drop_column("transcript_markdown")

    with op.batch_alter_table("clue") as batch_op:
        batch_op.add_column(sa.Column("document_file_path", sa.Text(), nullable=True))
        batch_op.drop_column("document_markdown")

    with op.batch_alter_table("npc") as batch_op:
        batch_op.add_column(sa.Column("profile_file_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("memory_file_path", sa.Text(), nullable=True))
        batch_op.drop_column("profile_markdown")
        batch_op.drop_column("memory_markdown")

    with op.batch_alter_table("session") as batch_op:
        batch_op.add_column(sa.Column("story_file_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("history_file_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("truth_file_path", sa.Text(), nullable=True))
        batch_op.drop_column("story_markdown")
        batch_op.drop_column("history_markdown")
        batch_op.drop_column("truth_markdown")
        batch_op.drop_column("latest_action_payload")
        batch_op.drop_column("ai_generation_log_entries")
