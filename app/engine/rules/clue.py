"""线索规则模块。"""

from app.models.character import KnowledgeEntryModel
from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class ClueRule:
    """处理地点调查、访问令牌与条件线索。"""

    name = "clue"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """在调查动作中收集当前位置已满足条件的线索。"""

        if not context.accepted or action.action_type != "investigate":
            return {"investigation": {"discovered_clues": [], "granted_access_tokens": []}}

        current_location = context.player.character.current_location
        if current_location is None:
            context.reject("Player has no current location.")
            return {"investigation": {"discovered_clues": [], "granted_access_tokens": []}}

        granted_access_tokens = self._grant_location_access_tokens(context)
        discovered = []
        player_character = context.player.character
        for clue in context.clues:
            if clue.current_location_id != current_location.id or not clue.is_movable:
                continue
            if not self._is_discoverable(clue.discovery_rule, context):
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

        return {
            "investigation": {
                "discovered_clues": discovered,
                "granted_access_tokens": granted_access_tokens,
            }
        }

    @staticmethod
    def _grant_location_access_tokens(context: ActionExecutionContext) -> list[str]:
        current_location = context.player.character.current_location
        if current_location is None or context.player.state is None:
            return []

        granted_tokens: list[str] = []
        configured_tokens = current_location.status_flags.get("investigate_grants_access_tokens", [])
        unlocked_access = list(context.player.state.unlocked_access)
        for token in configured_tokens:
            if not isinstance(token, str) or not token:
                continue
            if token in unlocked_access:
                continue
            unlocked_access.append(token)
            granted_tokens.append(token)
        if granted_tokens:
            context.player.state.unlocked_access = unlocked_access
        return granted_tokens

    @staticmethod
    def _is_discoverable(discovery_rule: dict, context: ActionExecutionContext) -> bool:
        required_tokens = discovery_rule.get("required_access_tokens", [])
        if required_tokens:
            unlocked_access = []
            if context.player.state is not None:
                unlocked_access = context.player.state.unlocked_access
            if not set(required_tokens).issubset(set(unlocked_access)):
                return False

        min_time_minute = discovery_rule.get("min_time_minute")
        if isinstance(min_time_minute, int) and context.session.current_time_minute < min_time_minute:
            return False

        return True
