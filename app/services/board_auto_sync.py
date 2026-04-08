from app.models import BoardItemModel


class BoardAutoSyncService:
    """负责基于世界状态自动补齐系统生成的侦探板卡片。"""

    def sync_bootstrap(self, *, player, game_map) -> None:
        board = player.detective_board
        current_location = player.character.current_location
        if board is None or current_location is None:
            return

        unlocked_access = player.state.unlocked_access if player.state is not None else []
        reachable_locations = self._reachable_locations(current_location, game_map.connections, unlocked_access)
        self._ensure_location_items(board, reachable_locations)

    def sync_after_action(self, *, player, game_map, clues, scene_snapshot, state_delta_summary) -> None:
        board = player.detective_board
        if board is None:
            return

        reachable_keys = [item.get("key") for item in scene_snapshot.details.get("reachable_locations", []) if item.get("key")]
        if reachable_keys:
            locations_by_key = {location.key: location for location in game_map.locations}
            self._ensure_location_items(
                board,
                [locations_by_key[key] for key in reachable_keys if key in locations_by_key],
            )

        discovered_keys = [item.get("key") for item in state_delta_summary.get("investigation", {}).get("discovered_clues", []) if item.get("key")]
        if discovered_keys:
            clues_by_key = {clue.key: clue for clue in clues}
            self._ensure_clue_items(
                board,
                [clues_by_key[key] for key in discovered_keys if key in clues_by_key],
            )

    def _ensure_location_items(self, board, locations) -> None:
        existing_refs = {(item.target_type, item.target_ref_id) for item in board.items}
        for location in locations:
            target_ref_id = str(location.id)
            if ("location", target_ref_id) in existing_refs:
                continue
            board.items.append(
                BoardItemModel(
                    target_type="location",
                    target_ref_id=target_ref_id,
                    title=location.name,
                    content=location.description,
                )
            )
            existing_refs.add(("location", target_ref_id))

    def _ensure_clue_items(self, board, clues) -> None:
        existing_refs = {(item.target_type, item.target_ref_id) for item in board.items}
        for clue in clues:
            target_ref_id = str(clue.id)
            if ("clue", target_ref_id) in existing_refs:
                continue
            board.items.append(
                BoardItemModel(
                    target_type="clue",
                    target_ref_id=target_ref_id,
                    title=clue.name,
                    content=clue.description or clue.name,
                )
            )
            existing_refs.add(("clue", target_ref_id))

    def _reachable_locations(self, current_location, connections, unlocked_access) -> list:
        reachable = {}
        for connection in connections:
            if not self._connection_is_accessible(connection, unlocked_access):
                continue
            if connection.from_location_id == current_location.id:
                reachable[connection.to_location_id] = connection.to_location
            elif not connection.is_one_way and connection.to_location_id == current_location.id:
                reachable[connection.from_location_id] = connection.from_location
        return sorted(reachable.values(), key=lambda location: location.key)

    @staticmethod
    def _connection_is_accessible(connection, unlocked_access: list[str]) -> bool:
        if connection.is_hidden or connection.is_locked:
            return False
        required_token = connection.access_rule.get("required_token")
        if isinstance(required_token, str) and required_token:
            return required_token in unlocked_access
        return True
