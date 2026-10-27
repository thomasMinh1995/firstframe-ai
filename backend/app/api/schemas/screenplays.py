"""Editable screenplay text; source snapshots are supplied only by the server."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.schemas.scenes import SceneId


class ScriptBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: SceneId
    kind: Literal["action", "dialogue"]
    text: str = Field(default="", max_length=10000)
    speaker: str = Field(default="", max_length=200)


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: SceneId
    source_scene_id: SceneId
    heading: str = Field(default="", max_length=500)
    blocks: list[ScriptBlock] = Field(default_factory=list, max_length=200)


class ScreenplayEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: SceneId
    version: int = Field(ge=1)
    scenes: list[ScriptScene] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def check_size_and_ids(self):
        ids = [s.id for s in self.scenes] + [b.id for s in self.scenes for b in s.blocks]
        sources = [s.source_scene_id for s in self.scenes]
        if len(set(ids)) != len(ids) or len(set(sources)) != len(sources):
            raise ValueError("Screenplay scene/block IDs must be unique.")
        if sum(len(s.blocks) for s in self.scenes) > 1000 or sum(
            len(s.heading) + sum(len(b.text) + len(b.speaker) for b in s.blocks) for s in self.scenes
        ) > 200000:
            raise ValueError("Screenplay exceeds text/block limits.")
        return self


class StartScreenplay(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    request_id: SceneId
