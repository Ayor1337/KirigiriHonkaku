from app.schemas.action import SoftStatePatch


def test_soft_state_patch_rejects_hard_state_keys():
    patch = SoftStatePatch.model_validate(
        {
            "allowed": False,
            "updates": {"current_time_minute": 120, "attitude_to_player": "guarded"},
        }
    )

    assert "current_time_minute" in patch.rejected_keys
    assert patch.applied_updates == {"attitude_to_player": "guarded"}
