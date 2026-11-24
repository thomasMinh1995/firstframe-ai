"""Server-owned attribution; accepting a draft is not an author constraint."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TextProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Literal["author_input", "ai_proposal", "legacy_unknown"] = "legacy_unknown"
    author_confirmed: bool = False

    @property
    def is_author_choice(self) -> bool:
        return self.origin == "author_input" or self.author_confirmed
