from app.schemas.action import SoftStatePatch


from app.core.config import Settings
from app.main import build_container


from pathlib import Path
from uuid import uuid4

def test_build_container_uses_fallback_runtime_without_provider_config():
    runtime_root = Path("tests_runtime") / uuid4().hex
    runtime_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{runtime_root / 'test.db'}",
        data_root=runtime_root / "data",
        auto_create_schema=True,
    )

    try:
        container = build_container(settings)
        assert container.ai_runtime.__class__.__name__ == "FallbackNarrativeRuntime"
    finally:
        if runtime_root.exists():
            import shutil

            shutil.rmtree(runtime_root, ignore_errors=True)


def test_soft_state_patch_rejects_hard_state_keys():
    patch = SoftStatePatch.model_validate(
        {
            "allowed": False,
            "npc_updates": {
                "journalist": {
                    "current_time_minute": 120,
                    "attitude_to_player": "guarded",
                    "emotion_tag": "wary",
                }
            },
            "dialogue_updates": {"tag_flags": {"tone": "tense"}},
        }
    )

    assert "journalist.current_time_minute" in patch.rejected_keys
    assert patch.npc_updates == {
        "journalist": {
            "attitude_to_player": "guarded",
            "emotion_tag": "wary",
        }
    }
    assert patch.dialogue_updates == {"tag_flags": {"tone": "tense"}}
