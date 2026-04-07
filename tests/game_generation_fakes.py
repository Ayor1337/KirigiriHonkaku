from types import SimpleNamespace

from app.ai.game_generation import GameGenerationRuntime, ProgressCallback
from app.schemas.world_generation import WorldBlueprint
from app.seeds.world import DefaultWorldSeedProvider


class StaticGameGenerationRuntime(GameGenerationRuntime):
    def generate(self, *, session_uuid: str, progress_callback: ProgressCallback = None) -> WorldBlueprint:
        seed = DefaultWorldSeedProvider().resolve(
            SimpleNamespace(
                case_template_key="case-manor",
                map_template_key="map-manor",
                truth_template_key="truth-manor",
            )
        )
        return WorldBlueprint.model_validate(
            {
                "title": f"Generated Case {session_uuid[:8]}",
                **seed,
            }
        )
