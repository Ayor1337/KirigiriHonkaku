"""内置世界模板注册表。"""

from copy import deepcopy


class TemplateCombinationNotRegisteredError(ValueError):
    """会话选择的模板组合未注册。"""


MANOR_MAP_TEMPLATE = {
    "display_name": "Moonview Manor",
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
}

MANOR_CASE_TEMPLATE = {
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
            "key": "gate-key",
            "name": "Gate Key",
            "description": "一把能打开庭院侧门的旧钥匙。",
            "clue_type": "physical",
            "initial_holder_character_key": "caretaker",
            "current_holder_character_key": "caretaker",
            "is_key_clue": True,
            "document_markdown": "# Gate Key\n钥匙边缘沾有新鲜泥土。\n",
        },
        {
            "key": "torn-note",
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
}

MANOR_TRUTH_TEMPLATE = {
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
}

THEATER_MAP_TEMPLATE = {
    "display_name": "Velvet Hour Theater",
    "locations": [
        {
            "key": "stage-lobby",
            "name": "Stage Lobby",
            "description": "剧院后台入口，公告栏与通行凭证都集中在这里。",
            "location_type": "hub",
            "visibility_level": "public",
            "status_flags": {
                "investigate_grants_access_tokens": ["backstage-pass"],
            },
        },
        {
            "key": "main-stage",
            "name": "Main Stage",
            "description": "彩排和公开说明经常发生的舞台中心。",
            "location_type": "interior",
            "visibility_level": "public",
            "parent_key": "stage-lobby",
        },
        {
            "key": "dressing-room",
            "name": "Dressing Room",
            "description": "主演更衣和短暂休息的房间。",
            "location_type": "interior",
            "visibility_level": "restricted",
            "parent_key": "stage-lobby",
        },
        {
            "key": "trap-storage",
            "name": "Trap Storage",
            "description": "存放机关道具和旧账本的狭窄储藏间。",
            "location_type": "interior",
            "visibility_level": "restricted",
            "parent_key": "stage-lobby",
        },
        {
            "key": "lighting-booth",
            "name": "Lighting Booth",
            "description": "俯瞰舞台的灯光控制间。",
            "location_type": "interior",
            "visibility_level": "restricted",
            "parent_key": "main-stage",
        },
    ],
    "connections": [
        {
            "from_location_key": "stage-lobby",
            "to_location_key": "main-stage",
            "connection_type": "curtain-door",
        },
        {
            "from_location_key": "stage-lobby",
            "to_location_key": "dressing-room",
            "connection_type": "corridor",
        },
        {
            "from_location_key": "dressing-room",
            "to_location_key": "main-stage",
            "connection_type": "backstage-door",
        },
        {
            "from_location_key": "main-stage",
            "to_location_key": "lighting-booth",
            "connection_type": "ladder",
        },
        {
            "from_location_key": "stage-lobby",
            "to_location_key": "trap-storage",
            "connection_type": "service-door",
            "access_rule": {"required_token": "backstage-pass"},
        },
    ],
}

THEATER_CASE_TEMPLATE = {
    "player": {
        "display_name": "Detective Kirigiri",
        "public_identity": "Guest Investigator",
        "template_name": "Detective",
        "trait_text": "擅长从舞台调度和人物关系里反推出隐藏动机。",
        "background_text": "受邀来调查一场彩排事故背后的真相。",
        "start_location_key": "stage-lobby",
        "unlocked_access": ["stage-lobby"],
        "status_flags": {
            "can_counterattack_culprit": False,
            "can_fabricate_evidence": False,
        },
    },
    "npcs": [
        {
            "key": "stage-manager",
            "display_name": "Stage Manager Sena",
            "public_identity": "Stage Manager",
            "role_type": "stage-manager",
            "location_key": "main-stage",
            "attitude_to_player": "guarded",
            "alertness_level": "medium",
            "emotion_tag": "tense",
            "schedule_mode": "cue-control",
            "schedule_entries": [
                {
                    "start_minute": 0,
                    "end_minute": 10,
                    "behavior_type": "briefing",
                    "behavior_description": "在主舞台监督彩排说明。",
                    "target_location_key": "main-stage",
                    "priority": 1,
                },
                {
                    "start_minute": 10,
                    "end_minute": 60,
                    "behavior_type": "conceal",
                    "behavior_description": "前往机关储藏间处理不该被看见的账页。",
                    "target_location_key": "trap-storage",
                    "priority": 2,
                },
            ],
            "profile_markdown": "# Stage Manager Sena\n负责整场演出的调度与机关管理。\n",
            "memory_markdown": "# Memory\n她担心有人发现被烧毁又重写的账页。\n",
        },
        {
            "key": "lead-actor",
            "display_name": "Lead Actor Mio",
            "public_identity": "Lead Actor",
            "role_type": "actor",
            "location_key": "dressing-room",
            "attitude_to_player": "uneasy",
            "alertness_level": "low",
            "emotion_tag": "irritated",
            "schedule_mode": "rehearsal",
            "schedule_entries": [
                {
                    "start_minute": 0,
                    "end_minute": 60,
                    "behavior_type": "wait",
                    "behavior_description": "在更衣室反复核对自己的出场顺序。",
                    "target_location_key": "dressing-room",
                    "priority": 1,
                }
            ],
            "profile_markdown": "# Lead Actor Mio\n对剧团财务问题一无所知，却经常被当成替罪羊。\n",
            "memory_markdown": "# Memory\n她记得舞台监督在事故前独自去了储藏间。\n",
        },
        {
            "key": "producer",
            "display_name": "Producer Ayame",
            "public_identity": "Producer",
            "role_type": "producer",
            "location_key": "stage-lobby",
            "attitude_to_player": "curious",
            "alertness_level": "low",
            "emotion_tag": "focused",
            "schedule_mode": "oversight",
            "schedule_entries": [
                {
                    "start_minute": 0,
                    "end_minute": 60,
                    "behavior_type": "observe",
                    "behavior_description": "在后台入口关注每个人的动向。",
                    "target_location_key": "stage-lobby",
                    "priority": 1,
                }
            ],
            "profile_markdown": "# Producer Ayame\n掌握预算，但对台前台后的矛盾保持沉默。\n",
            "memory_markdown": "# Memory\n她知道剧团有人在伪造一部分成本记录。\n",
        },
    ],
    "clues": [
        {
            "key": "cue-sheet",
            "name": "Cue Sheet",
            "description": "写满临时修改标记的彩排提示单。",
            "clue_type": "document",
            "initial_location_key": "main-stage",
            "current_location_key": "main-stage",
            "document_markdown": "# Cue Sheet\n有人把一处机关检修时间悄悄改晚了。\n",
        },
        {
            "key": "critic-card",
            "name": "Critic Card",
            "description": "制片人随身携带的一张来宾通行卡。",
            "clue_type": "physical",
            "initial_holder_character_key": "producer",
            "current_holder_character_key": "producer",
            "document_markdown": "# Critic Card\n卡片背面写着一串与财务柜编号相关的字样。\n",
        },
        {
            "key": "burned-ledger-page",
            "name": "Burned Ledger Page",
            "description": "一页被烧过边角的账本残页，记录被人为改写过。",
            "clue_type": "document",
            "initial_location_key": "trap-storage",
            "current_location_key": "trap-storage",
            "is_key_clue": True,
            "discovery_rule": {
                "required_access_tokens": ["backstage-pass"],
            },
            "document_markdown": "# Burned Ledger Page\n残页显示舞台机关维修费用被重复报销。\n",
        },
    ],
    "events": [
        {
            "name": "Opening Notes",
            "event_type": "briefing",
            "description": "彩排开始前，后台入口短暂形成公开说明场。",
            "location_key": "stage-lobby",
            "start_minute": 0,
            "end_minute": 15,
            "is_public_event": True,
            "rule_flags": {
                "public_context_key": "opening-notes",
                "source": "scheduled_event",
            },
            "participants": [
                {"character_key": "player", "participant_role": "observer", "attendance_state": "present"},
                {"character_key": "producer", "participant_role": "host", "attendance_state": "present"},
            ],
        }
    ],
}

THEATER_TRUTH_TEMPLATE = {
    "culprit_npc_key": "stage-manager",
    "required_clue_keys": ["burned-ledger-page"],
    "supporting_clue_keys": ["cue-sheet"],
    "public_accusation_event_keys": ["opening-notes"],
    "countermeasure_plan": {
        "indirect": ["raise_alertness", "apply_pressure"],
        "direct": ["counterattack_in_private"],
    },
    "false_verdict_targets": ["lead-actor"],
    "private_encounter_rules": {
        "violent_flag": "can_counterattack_culprit",
        "fabricate_flag": "can_fabricate_evidence",
    },
}

CASE_TEMPLATES = {
    "case-manor": MANOR_CASE_TEMPLATE,
    "case-theater": THEATER_CASE_TEMPLATE,
}
MAP_TEMPLATES = {
    "map-manor": MANOR_MAP_TEMPLATE,
    "map-theater": THEATER_MAP_TEMPLATE,
}
TRUTH_TEMPLATES = {
    "truth-manor": MANOR_TRUTH_TEMPLATE,
    "truth-theater": THEATER_TRUTH_TEMPLATE,
}

REGISTERED_TEMPLATE_COMBINATIONS = {
    ("case-manor", "map-manor", "truth-manor"): ("case-manor", "map-manor", "truth-manor"),
    ("case-zero", "map-zero", "truth-zero"): ("case-manor", "map-manor", "truth-manor"),
    ("case-action", "map-action", "truth-action"): ("case-manor", "map-manor", "truth-manor"),
    ("case-repository", "map-repository", "truth-repository"): ("case-manor", "map-manor", "truth-manor"),
    ("case-theater", "map-theater", "truth-theater"): ("case-theater", "map-theater", "truth-theater"),
}


class DefaultWorldSeedProvider:
    """根据模板 key 提供可运行的世界 seed。"""

    def resolve(self, session) -> dict:
        combo = (
            session.case_template_key,
            session.map_template_key,
            session.truth_template_key,
        )
        canonical_combo = REGISTERED_TEMPLATE_COMBINATIONS.get(combo)
        if canonical_combo is None:
            raise TemplateCombinationNotRegisteredError(combo)

        case_key, map_key, truth_key = canonical_combo
        seed = {
            "map": {
                "template_key": session.map_template_key,
                "display_name": MAP_TEMPLATES[map_key]["display_name"],
            },
            "locations": deepcopy(MAP_TEMPLATES[map_key]["locations"]),
            "connections": deepcopy(MAP_TEMPLATES[map_key]["connections"]),
            "player": deepcopy(CASE_TEMPLATES[case_key]["player"]),
            "npcs": deepcopy(CASE_TEMPLATES[case_key]["npcs"]),
            "clues": deepcopy(CASE_TEMPLATES[case_key]["clues"]),
            "events": deepcopy(CASE_TEMPLATES[case_key]["events"]),
            "truth": deepcopy(TRUTH_TEMPLATES[truth_key]),
        }
        seed["player"]["template_key"] = session.case_template_key
        return seed
