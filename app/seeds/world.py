"""内置最小世界 seed。"""

from copy import deepcopy


DEFAULT_WORLD_SEED = {
    "map": {
        "display_name": "Moonview Manor",
    },
    "locations": [
        {
            "key": "entrance-hall",
            "name": "Entrance Hall",
            "description": "庄园的主入口与交通枢纽。",
            "location_type": "hub",
            "visibility_level": "public",
        },
        {
            "key": "archive-room",
            "name": "Archive Room",
            "description": "存放旧档案和纸质材料的房间。",
            "location_type": "interior",
            "visibility_level": "restricted",
            "parent_key": "entrance-hall",
        },
        {
            "key": "garden-gate",
            "name": "Garden Gate",
            "description": "通往庭院外侧的小门。",
            "location_type": "exterior",
            "visibility_level": "public",
            "parent_key": "entrance-hall",
        },
    ],
    "connections": [
        {
            "from_location_key": "entrance-hall",
            "to_location_key": "archive-room",
            "connection_type": "door",
        },
        {
            "from_location_key": "entrance-hall",
            "to_location_key": "garden-gate",
            "connection_type": "gate",
        },
    ],
    "player": {
        "display_name": "Detective Kirigiri",
        "public_identity": "Independent Detective",
        "template_name": "Detective",
        "trait_text": "冷静、谨慎、擅长交叉验证证词。",
        "background_text": "受邀前来调查庄园中的异常事件。",
        "start_location_key": "entrance-hall",
        "unlocked_access": ["entrance-hall"],
        "status_flags": {
            "can_counterattack_culprit": False,
            "can_fabricate_evidence": False,
        },
    },
    "npcs": [
        {
            "key": "caretaker",
            "display_name": "Caretaker Iori",
            "public_identity": "Groundskeeper",
            "role_type": "caretaker",
            "location_key": "entrance-hall",
            "attitude_to_player": "guarded",
            "alertness_level": "medium",
            "emotion_tag": "wary",
            "schedule_mode": "routine",
            "schedule_entries": [
                {
                    "start_minute": 0,
                    "end_minute": 120,
                    "behavior_type": "patrol",
                    "behavior_description": "巡视大厅与庭院入口。",
                    "target_location_key": "garden-gate",
                    "priority": 1,
                }
            ],
            "profile_markdown": "# Caretaker Iori\n负责庄园日常维护。\n",
            "memory_markdown": "# Memory\n他记得案发前夜有人经过庭院门。\n",
        },
        {
            "key": "journalist",
            "display_name": "Journalist Ren",
            "public_identity": "Freelance Reporter",
            "role_type": "journalist",
            "location_key": "archive-room",
            "attitude_to_player": "curious",
            "alertness_level": "low",
            "emotion_tag": "focused",
            "schedule_mode": "research",
            "schedule_entries": [
                {
                    "start_minute": 0,
                    "end_minute": 120,
                    "behavior_type": "research",
                    "behavior_description": "在档案室查找与庄园历史有关的材料。",
                    "target_location_key": "archive-room",
                    "priority": 1,
                }
            ],
            "profile_markdown": "# Journalist Ren\n专门追踪旧案与家族丑闻。\n",
            "memory_markdown": "# Memory\n他怀疑庄园主人隐瞒了过去的事故。\n",
        },
    ],
    "clues": [
        {
            "name": "Gate Key",
            "description": "一把能打开庭院侧门的旧钥匙。",
            "clue_type": "physical",
            "initial_holder_character_key": "caretaker",
            "current_holder_character_key": "caretaker",
            "is_key_clue": True,
            "document_markdown": "# Gate Key\n钥匙边缘沾有新鲜泥土。\n",
        },
        {
            "name": "Torn Note",
            "description": "在档案室文件夹里发现的一页残缺便条。",
            "clue_type": "document",
            "initial_location_key": "archive-room",
            "current_location_key": "archive-room",
            "is_time_sensitive": False,
            "document_markdown": "# Torn Note\n便条提到“晚八点后不要走正门”。\n",
        },
    ],
    "events": [
        {
            "name": "Evening Briefing",
            "event_type": "briefing",
            "description": "开局时所有关键人物都在大厅交换信息。",
            "location_key": "entrance-hall",
            "start_minute": 0,
            "end_minute": 20,
            "is_public_event": True,
            "rule_flags": {
                "public_context_key": "evening-briefing",
                "source": "scheduled_event",
            },
            "participants": [
                {"character_key": "player", "participant_role": "observer", "attendance_state": "present"},
                {"character_key": "caretaker", "participant_role": "host", "attendance_state": "present"},
            ],
        }
    ],
    "truth": {
        "culprit_npc_key": "journalist",
        "required_clue_keys": ["torn-note"],
        "supporting_clue_keys": ["gate-key"],
        "public_accusation_event_keys": ["evening-briefing"],
        "countermeasure_plan": {
            "indirect": ["raise_alertness", "apply_pressure"],
            "direct": ["counterattack_in_private"],
        },
        "false_verdict_targets": ["caretaker"],
        "private_encounter_rules": {
            "violent_flag": "can_counterattack_culprit",
            "fabricate_flag": "can_fabricate_evidence",
        },
    },
}


class DefaultWorldSeedProvider:
    """根据模板 key 提供最小可运行的内置世界 seed。"""

    def resolve(self, session) -> dict:
        seed = deepcopy(DEFAULT_WORLD_SEED)
        seed["map"]["template_key"] = session.map_template_key
        seed["player"]["template_key"] = session.case_template_key
        return seed
