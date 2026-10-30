"""Editable screenplay text; source snapshots are supplied only by the server."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

from app.api.schemas.scenes import SceneId
from app.api.schemas.provenance import TextProvenance


class BlockText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["action", "dialogue"]
    text: str = Field(default="", max_length=10000)
    speaker: str = Field(default="", max_length=200)


class ScriptBlock(BlockText):
    id: SceneId


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: SceneId
    source_scene_id: SceneId
    heading: str = Field(default="", max_length=500)
    blocks: list[ScriptBlock] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def check_preview_limits(self):
        ids = [self.id, *[b.id for b in self.blocks]]
        if len(set(ids)) != len(ids) or len(self.heading) + sum(len(b.text) + len(b.speaker) for b in self.blocks) > 200000:
            raise ValueError("Scene block IDs must be unique and text must fit the screenplay limit.")
        return self


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


class SceneWritingRequest(StartScreenplay):
    scope: Literal["scene", "blocks"] = "scene"
    block_ids: list[SceneId] = Field(default_factory=list, max_length=20)
    review_id: SceneId | None = None
    note_id: SceneId | None = None
    target_scene_id: SceneId
    instructions: str = Field(default="", max_length=2000)


class SelectScreenplay(StartScreenplay):
    source_version_id: Literal["current"] | SceneId


class WrittenAction(BlockText):
    kind: Literal["action"]
    text: str = Field(min_length=1, max_length=10000)
    speaker: Literal[""] = ""


class WrittenDialogue(BlockText):
    kind: Literal["dialogue"]
    text: str = Field(min_length=1, max_length=10000)
    speaker: str = Field(min_length=1, max_length=200)


class WrittenScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str = Field(min_length=1, max_length=500)
    blocks: list[WrittenAction | WrittenDialogue] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_content(self):
        if not self.heading.strip() or any(not b.text.strip() or (b.kind == "dialogue" and not b.speaker.strip())
                                           or (b.kind == "action" and b.speaker != "") for b in self.blocks):
            raise ValueError("Written scene requires nonempty blocks and dialogue speakers.")
        if sum(len(b.text) + len(b.speaker) for b in self.blocks) + len(self.heading) > 200000:
            raise ValueError("Scene exceeds text limit.")
        return self


class SceneWritingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: WrittenScene


class ReviewSource(BaseModel):
    id: str
    label: str
    text: str
    category: Literal["screenplay", "author_choice", "context"]
    provenance: TextProvenance | None = None
    scene_id: SceneId | None = None
    block_id: SceneId | None = None
    field: Literal["text", "speaker", "heading", "choice", "context"]

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        data = handler(self)
        if self.provenance is None:
            data.pop("provenance", None)
        return data


class ReviewEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=1000)


class ScriptReviewNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["intent_mismatch", "craft", "uncertain"]
    observation: str = Field(min_length=1, max_length=2000)
    impact: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(default="", max_length=2000)
    evidence: list[ReviewEvidence] = Field(min_length=1, max_length=4)


class SceneReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: list[ScriptReviewNote] = Field(max_length=6)
    question: str = Field(default="", max_length=2000)


class SavedReviewNote(ScriptReviewNote):
    id: SceneId
    assessment: Literal["helpful", "misleading", "uncertain", "dismissed"] | None = None


class ReviewAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    assessment: Literal["helpful", "misleading", "uncertain", "dismissed"]


class BlockReplacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_id: SceneId
    expected: BlockText
    replacement: BlockText


class BlockRevisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replacements: list[BlockReplacement] = Field(min_length=1, max_length=20)
