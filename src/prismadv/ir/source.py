from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    file: str = ""

