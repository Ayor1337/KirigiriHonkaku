from uuid import UUID

from app.models import BoardItemModel, BoardLinkModel, BoardNoteModel, DetectiveBoardModel
from app.schemas.board import BoardSaveRequest, SessionBoardResponse


class BoardSessionNotFoundError(LookupError):
    """指定 session 不存在。"""


class DetectiveBoardNotFoundError(LookupError):
    """指定 session 下不存在 detective board。"""


class BoardValidationError(ValueError):
    """board 请求校验失败。"""


class BoardService:
    """负责侦探板的读取与整板覆盖保存。"""

    SUPPORTED_TARGET_TYPES = {"player", "npc", "clue", "location"}

    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    def get_board(self, session_id: str) -> SessionBoardResponse:
        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None:
                raise BoardSessionNotFoundError(session_id)

            player = uow.players.get_by_session(session_id)
            board = player.detective_board if player is not None else None
            if board is None:
                raise DetectiveBoardNotFoundError(session_id)

            return self._serialize_board(board)

    def save_board(self, session_id: str, payload: BoardSaveRequest) -> SessionBoardResponse:
        with self._uow_factory() as uow:
            session = uow.sessions.get(session_id)
            if session is None:
                raise BoardSessionNotFoundError(session_id)

            player = uow.players.get_by_session(session_id)
            board = player.detective_board if player is not None else None
            if board is None:
                raise DetectiveBoardNotFoundError(session_id)

            entity_index = self._build_entity_index(uow, player)
            self._validate_payload(payload, entity_index)

            board.board_layout_version = payload.board_layout_version
            board.links.clear()
            board.items.clear()
            board.notes.clear()
            uow.session.flush()

            item_by_client_key: dict[str, BoardItemModel] = {}
            for item in payload.items:
                board_item = BoardItemModel(
                    target_type=item.target_type,
                    target_ref_id=str(item.target_ref_id),
                    position_x=item.position_x,
                    position_y=item.position_y,
                    group_key=item.group_key,
                )
                board.items.append(board_item)
                item_by_client_key[item.client_key] = board_item

            for link in payload.links:
                board.links.append(
                    BoardLinkModel(
                        from_item=item_by_client_key[link.from_client_key],
                        to_item=item_by_client_key[link.to_client_key],
                        label=link.label,
                        style_key=link.style_key,
                    )
                )

            for note in payload.notes:
                board.notes.append(
                    BoardNoteModel(
                        content=note.content,
                        position_x=note.position_x,
                        position_y=note.position_y,
                    )
                )

            uow.session.flush()
            response = self._serialize_board(board)
            uow.commit()
            return response

    def _build_entity_index(self, uow, player) -> dict[str, set[str]]:
        game_map = uow.maps.get_by_session(str(player.session_id))
        return {
            "player": {str(player.id)},
            "npc": {str(item.id) for item in uow.npcs.list_by_session(str(player.session_id))},
            "clue": {str(item.id) for item in uow.clues.list_by_session(str(player.session_id))},
            "location": {str(item.id) for item in (game_map.locations if game_map is not None else [])},
        }

    def _validate_payload(self, payload: BoardSaveRequest, entity_index: dict[str, set[str]]) -> None:
        client_keys: set[str] = set()
        for item in payload.items:
            if item.client_key in client_keys:
                raise BoardValidationError("Board item client_key must be unique.")
            client_keys.add(item.client_key)

            if item.target_type not in self.SUPPORTED_TARGET_TYPES:
                raise BoardValidationError("Unsupported board item target type.")
            if str(item.target_ref_id) not in entity_index[item.target_type]:
                raise BoardValidationError("Board item target does not exist in current session.")

        for link in payload.links:
            if link.from_client_key not in client_keys or link.to_client_key not in client_keys:
                raise BoardValidationError("Board link must reference existing board items in request.")

    @staticmethod
    def _serialize_board(board: DetectiveBoardModel) -> SessionBoardResponse:
        items = sorted(board.items, key=lambda item: (item.created_at, str(item.id)))
        links = sorted(board.links, key=lambda item: (item.created_at, str(item.id)))
        notes = sorted(board.notes, key=lambda item: (item.created_at, str(item.id)))
        return SessionBoardResponse(
            id=board.id,
            board_layout_version=board.board_layout_version,
            items=[
                {
                    "id": item.id,
                    "target_type": item.target_type,
                    "target_ref_id": item.target_ref_id,
                    "position_x": item.position_x,
                    "position_y": item.position_y,
                    "group_key": item.group_key,
                }
                for item in items
            ],
            links=[
                {
                    "id": item.id,
                    "from_item_id": item.from_item_id,
                    "to_item_id": item.to_item_id,
                    "label": item.label,
                    "style_key": item.style_key,
                }
                for item in links
            ],
            notes=[
                {
                    "id": item.id,
                    "content": item.content,
                    "position_x": item.position_x,
                    "position_y": item.position_y,
                }
                for item in notes
            ],
        )

