"""NPC 调度规则模块。"""

from app.engine.rules.base import ActionExecutionContext
from app.schemas.action import ActionRequest


class NpcScheduleRule:
    """按当前时间片刷新 NPC 最小位置。"""

    name = "npc_schedule"

    def apply(self, action: ActionRequest, context: ActionExecutionContext) -> dict:
        """对所有会推进时间的动作执行一次最小日程刷新。"""

        if not context.accepted or action.action_type not in {"move", "talk", "investigate"}:
            return {"npc_schedule_checked": False, "moved_npcs": []}

        moved_npcs = []
        current_minute = context.session.current_time_minute
        for npc in context.npcs:
            if npc.state is None or npc.schedule is None:
                continue

            active_entries = [
                entry
                for entry in npc.schedule.entries
                if entry.start_minute <= current_minute < entry.end_minute and entry.target_location is not None
            ]
            if not active_entries:
                continue

            active_entries.sort(key=lambda entry: (-entry.priority, entry.start_minute))
            target_entry = active_entries[0]
            target_location = target_entry.target_location
            if target_location is None:
                continue
            if npc.state.current_location_id == target_location.id:
                continue

            npc.state.current_location = target_location
            npc.character.current_location = target_location
            moved_npcs.append(
                {
                    "npc_key": npc.template_key,
                    "to_location_key": target_location.key,
                }
            )

        return {
            "npc_schedule_checked": True,
            "moved_npcs": moved_npcs,
        }
