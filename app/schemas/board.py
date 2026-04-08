from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BoardItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_ref_id: UUID
    position_x: float | None = None
    position_y: float | None = None
    group_key: str | None = None


class BoardLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_item_id: UUID
    to_item_id: UUID
    label: str | None = None
    style_key: str | None = None


class BoardNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    position_x: float | None = None
    position_y: float | None = None


class SessionBoardResponse(BaseModel):
    id: UUID
    board_layout_version: int
    items: list[BoardItemResponse] = Field(default_factory=list)
    links: list[BoardLinkResponse] = Field(default_factory=list)
    notes: list[BoardNoteResponse] = Field(default_factory=list)


class BoardItemWriteRequest(BaseModel):
    client_key: str
    target_type: str
    target_ref_id: UUID
    position_x: float | None = None
    position_y: float | None = None
    group_key: str | None = None


class BoardLinkWriteRequest(BaseModel):
    from_client_key: str
    to_client_key: str
    label: str | None = None
    style_key: str | None = None


class BoardNoteWriteRequest(BaseModel):
    content: str
    position_x: float | None = None
    position_y: float | None = None


class BoardSaveRequest(BaseModel):
    board_layout_version: int = 1
    items: list[BoardItemWriteRequest] = Field(default_factory=list)
    links: list[BoardLinkWriteRequest] = Field(default_factory=list)
    notes: list[BoardNoteWriteRequest] = Field(default_factory=list)
