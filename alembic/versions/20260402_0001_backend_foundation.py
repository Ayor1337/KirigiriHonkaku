"""backend foundation

Revision ID: 20260402_0001
Revises:
Create Date: 2026-04-02 00:00:00
"""
"""Step 1 后端骨架的固定 schema 基线迁移。"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260402_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """创建 Step 1 与 Step 2 共同依赖的固定基线表结构。"""

    op.create_table(
        "session",
        sa.Column("uuid", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_time_minute", sa.Integer(), nullable=False),
        sa.Column("current_time_minute", sa.Integer(), nullable=False),
        sa.Column("incident_time_minute", sa.Integer(), nullable=True),
        sa.Column("exposure_value", sa.Integer(), nullable=False),
        sa.Column("exposure_level", sa.String(length=32), nullable=True),
        sa.Column("ending_type", sa.String(length=64), nullable=True),
        sa.Column("accusation_state", sa.String(length=64), nullable=True),
        sa.Column("case_template_key", sa.String(length=128), nullable=True),
        sa.Column("map_template_key", sa.String(length=128), nullable=True),
        sa.Column("truth_template_key", sa.String(length=128), nullable=True),
        sa.Column("story_file_path", sa.Text(), nullable=True),
        sa.Column("history_file_path", sa.Text(), nullable=True),
        sa.Column("truth_file_path", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )

    op.create_table(
        "map",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )

    op.create_table(
        "location",
        sa.Column("map_id", sa.Uuid(), nullable=False),
        sa.Column("parent_location_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_type", sa.String(length=64), nullable=False),
        sa.Column("visibility_level", sa.String(length=32), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("status_flags", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["map_id"], ["map.id"]),
        sa.ForeignKeyConstraint(["parent_location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "character",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("public_identity", sa.String(length=255), nullable=True),
        sa.Column("current_location_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("can_participate_dialogue", sa.Boolean(), nullable=False),
        sa.Column("can_hold_clue", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('player', 'npc')", name="character_kind"),
        sa.ForeignKeyConstraint(["current_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "player",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=128), nullable=True),
        sa.Column("template_name", sa.String(length=255), nullable=True),
        sa.Column("trait_text", sa.Text(), nullable=True),
        sa.Column("background_text", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id"),
        sa.UniqueConstraint("session_id"),
    )

    op.create_table(
        "player_state",
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("hp_state", sa.String(length=32), nullable=True),
        sa.Column("injury_state", sa.String(length=32), nullable=True),
        sa.Column("poison_state", sa.String(length=32), nullable=True),
        sa.Column("exposure_value", sa.Integer(), nullable=False),
        sa.Column("exposure_level", sa.String(length=32), nullable=True),
        sa.Column("status_flags", JSON_VARIANT, nullable=False),
        sa.Column("temporary_effects", JSON_VARIANT, nullable=False),
        sa.Column("unlocked_access", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id"),
    )

    op.create_table(
        "player_inventory",
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("money_amount", sa.Integer(), nullable=False),
        sa.Column("resource_flags", JSON_VARIANT, nullable=False),
        sa.Column("held_item_refs", JSON_VARIANT, nullable=False),
        sa.Column("equipped_item_refs", JSON_VARIANT, nullable=False),
        sa.Column("credential_refs", JSON_VARIANT, nullable=False),
        sa.Column("weapon_refs", JSON_VARIANT, nullable=False),
        sa.Column("document_refs", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id"),
    )

    op.create_table(
        "player_knowledge",
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id"),
    )

    op.create_table(
        "knowledge_topic",
        sa.Column("player_knowledge_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_knowledge_id"], ["player_knowledge.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "knowledge_entry",
        sa.Column("player_knowledge_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_ref_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance_level", sa.String(length=32), nullable=True),
        sa.Column("learned_at_minute", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_knowledge_id"], ["player_knowledge.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["knowledge_topic.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "detective_board",
        sa.Column("player_id", sa.Uuid(), nullable=False),
        sa.Column("board_layout_version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["player.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id"),
    )

    op.create_table(
        "board_item",
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_ref_id", sa.String(length=36), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=True),
        sa.Column("position_y", sa.Float(), nullable=True),
        sa.Column("group_key", sa.String(length=128), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["detective_board.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "board_link",
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("from_item_id", sa.Uuid(), nullable=False),
        sa.Column("to_item_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("style_key", sa.String(length=128), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["detective_board.id"]),
        sa.ForeignKeyConstraint(["from_item_id"], ["board_item.id"]),
        sa.ForeignKeyConstraint(["to_item_id"], ["board_item.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "board_note",
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=True),
        sa.Column("position_y", sa.Float(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["detective_board.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "npc",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=128), nullable=True),
        sa.Column("role_type", sa.String(length=128), nullable=True),
        sa.Column("profile_file_path", sa.Text(), nullable=True),
        sa.Column("memory_file_path", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id"),
    )

    op.create_table(
        "npc_state",
        sa.Column("npc_id", sa.Uuid(), nullable=False),
        sa.Column("current_location_id", sa.Uuid(), nullable=True),
        sa.Column("attitude_to_player", sa.String(length=32), nullable=True),
        sa.Column("alertness_level", sa.String(length=32), nullable=True),
        sa.Column("emotion_tag", sa.String(length=32), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("is_in_event", sa.Boolean(), nullable=False),
        sa.Column("is_under_pressure", sa.Boolean(), nullable=False),
        sa.Column("state_flags", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["current_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["npc_id"], ["npc.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("npc_id"),
    )

    op.create_table(
        "npc_schedule",
        sa.Column("npc_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_mode", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["npc_id"], ["npc.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("npc_id"),
    )

    op.create_table(
        "schedule_entry",
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("behavior_type", sa.String(length=64), nullable=False),
        sa.Column("behavior_description", sa.Text(), nullable=True),
        sa.Column("target_location_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["npc_schedule.id"]),
        sa.ForeignKeyConstraint(["target_location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "connection",
        sa.Column("map_id", sa.Uuid(), nullable=False),
        sa.Column("from_location_id", sa.Uuid(), nullable=False),
        sa.Column("to_location_id", sa.Uuid(), nullable=False),
        sa.Column("connection_type", sa.String(length=64), nullable=True),
        sa.Column("access_rule", JSON_VARIANT, nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("is_one_way", sa.Boolean(), nullable=False),
        sa.Column("is_dangerous", sa.Boolean(), nullable=False),
        sa.Column("time_window_rule", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["map_id"], ["map.id"]),
        sa.ForeignKeyConstraint(["to_location_id"], ["location.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "clue",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("clue_type", sa.String(length=64), nullable=False),
        sa.Column("initial_location_id", sa.Uuid(), nullable=True),
        sa.Column("initial_holder_character_id", sa.Uuid(), nullable=True),
        sa.Column("current_location_id", sa.Uuid(), nullable=True),
        sa.Column("current_holder_character_id", sa.Uuid(), nullable=True),
        sa.Column("is_key_clue", sa.Boolean(), nullable=False),
        sa.Column("is_movable", sa.Boolean(), nullable=False),
        sa.Column("is_time_sensitive", sa.Boolean(), nullable=False),
        sa.Column("clue_state", sa.String(length=64), nullable=True),
        sa.Column("document_file_path", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN initial_location_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN initial_holder_character_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="clue_initial_owner_xor",
        ),
        sa.CheckConstraint(
            "(CASE WHEN current_location_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN current_holder_character_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="clue_current_owner_xor",
        ),
        sa.ForeignKeyConstraint(["current_holder_character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["current_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["initial_holder_character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["initial_location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "event",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("event_state", sa.String(length=64), nullable=True),
        sa.Column("is_public_event", sa.Boolean(), nullable=False),
        sa.Column("rule_flags", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "event_participant",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("participant_role", sa.String(length=64), nullable=True),
        sa.Column("attendance_state", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "dialogue",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("dialogue_type", sa.String(length=64), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=True),
        sa.Column("summary_file_path", sa.Text(), nullable=True),
        sa.Column("transcript_file_path", sa.Text(), nullable=True),
        sa.Column("tag_flags", JSON_VARIANT, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "dialogue_participant",
        sa.Column("dialogue_id", sa.Uuid(), nullable=False),
        sa.Column("character_id", sa.Uuid(), nullable=False),
        sa.Column("participant_role", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"]),
        sa.ForeignKeyConstraint(["dialogue_id"], ["dialogue.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "utterance",
        sa.Column("dialogue_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("speaker_character_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tone_tag", sa.String(length=64), nullable=True),
        sa.Column("utterance_flags", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["dialogue_id"], ["dialogue.id"]),
        sa.ForeignKeyConstraint(["speaker_character_id"], ["character.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dialogue_id", "sequence_no", name="uq_utterance_dialogue_sequence"),
    )


def downgrade() -> None:
    """按依赖逆序回滚基线表结构。"""

    for table_name in [
        "utterance",
        "dialogue_participant",
        "dialogue",
        "event_participant",
        "event",
        "clue",
        "connection",
        "schedule_entry",
        "npc_schedule",
        "npc_state",
        "npc",
        "board_note",
        "board_link",
        "board_item",
        "detective_board",
        "knowledge_entry",
        "knowledge_topic",
        "player_knowledge",
        "player_inventory",
        "player_state",
        "player",
        "character",
        "location",
        "map",
        "session",
    ]:
        op.drop_table(table_name)


