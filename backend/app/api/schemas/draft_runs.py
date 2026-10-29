"""Server-owned progress for checkpointed draft runs."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ItemStatus = Literal[
    "pending", "running", "needs_input", "completed", "warning", "failed",
    "interrupted", "cancelled", "skipped", "unknown",
]
ItemKind = Literal[
    "analysis", "intent", "plan", "plan_review", "outline", "write",
    "review", "review_scene", "draft",
]


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ItemKind
    id: str | None = None
    candidate_revision: int = Field(ge=0)


class WorkflowItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: ItemKind
    scene_id: str | None = None
    status: ItemStatus = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    result: ArtifactRef | None = None
    error_code: Literal[
        "provider_error", "unknown_result", "restart", "review_unavailable",
        "cancelled", "candidate_incomplete", "not_run",
    ] | None = None
    children: list["WorkflowItem"] = Field(default_factory=list, max_length=6)


class DraftRunResponse(BaseModel):
    # Whitelist public fields so future private run metadata cannot leak through GET.
    model_config = ConfigDict(extra="ignore")
    id: str
    project_id: str
    source_revision: int = Field(ge=0)
    created_at: str | None = None
    updated_at: str | None = None
    revision_instructions: str = ""
    affected_scene_ids: list[str] = Field(default_factory=list)
    status: Literal["running", "needs_input", "ready", "partial", "failed", "interrupted", "cancelled"]
    step: str
    sending: bool
    cancel_requested: bool
    candidate_revision: int = Field(ge=0)
    completed_scenes: int = Field(ge=0)
    total_scenes: int = Field(ge=0)
    error: str | None
    review_error: str | None
    adopted_revision: int | None
    progress_version: Literal[0, 1]
    progress_revision: int = Field(ge=0)
    workflow_items: list[WorkflowItem]
    can_continue: bool
    continue_block_reason: Literal[
        "adopted", "cancelled", "not_resumable", "provider_unavailable",
        "configuration_changed", "unknown_result", "candidate_edited",
    ] | None
    continue_block_message: str | None
