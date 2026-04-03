"""线索规则模块。"""

from app.models.character import KnowledgeEntryModel
from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class ClueRule:
    """处理地点调查与线索收集。"""

    name = "clue"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """在调查动作中收集当前位置的可移动线索。"""

        if not context.accepted or action.action_type != "investigate":
            return {"investigation": {"discovered_clues": []}}

        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return {"investigation": {"discovered_clues": []}}

        discovered = []
        player_character = context.player.character
        for clue in context.clues:
            if clue.current_location_id != current_location.id or not clue.is_movable:
                continue
            clue.current_location = None
            clue.current_location_id = None
            clue.current_holder_character = player_character
            clue.current_holder_character_id = player_character.id
            clue.clue_state = "collected"
            context.player.knowledge.entries.append(
                KnowledgeEntryModel(
                    source_type="investigate",
                    source_ref_id=clue.key,
                    title=clue.name,
                    content=clue.description or clue.name,
                    importance_level="high" if clue.is_key_clue else "medium",
                    learned_at_minute=context.session.current_time_minute,
                )
            )
            discovered.append(
                {
                    "key": clue.key,
                    "name": clue.name,
                    "clue_type": clue.clue_type,
                }
            )

        return {"investigation": {"discovered_clues": discovered}}

