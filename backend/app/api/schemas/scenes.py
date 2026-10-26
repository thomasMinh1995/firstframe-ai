from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SceneId = Annotated[str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]
SceneText = Annotated[str, Field(max_length=2000)]
StagingKey = Literal["blocking", "performance", "setting", "lighting", "color", "costume",
                     "moment", "shot", "angle", "composition"]


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: SceneId
    title: str = Field(default="", max_length=200)
    action: str = Field(default="", max_length=10000)
    location: str = Field(default="", max_length=500)
    time: str = Field(default="", max_length=200)
    characters: SceneText = ""
    goal: SceneText = ""
    purpose: SceneText = ""
    viewer_intent: SceneText = ""
    keep_or_avoid: SceneText = ""
    staging_choices: dict[StagingKey, SceneText] = Field(default_factory=dict)


class SceneOutlineEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: SceneId
    version: int = Field(ge=1)
    scenes: list[Scene] = Field(max_length=60)

    @model_validator(mode="after")
    def unique_ids(self) -> "SceneOutlineEdit":
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("Scene IDs must be unique.")
        return self


class StartSceneOutline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=0)
    # Current means the saved draft, never a client-supplied source snapshot.
    source_version_id: str = Field(default="current", min_length=1, max_length=100)
