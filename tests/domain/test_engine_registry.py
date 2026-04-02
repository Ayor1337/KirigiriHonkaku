from app.engine.service import GameEngine


def test_game_engine_registers_foundation_rule_modules():
    engine = GameEngine()

    assert engine.module_names == [
        "time",
        "map",
        "npc_schedule",
        "clue",
        "exposure",
        "accusation",
    ]
