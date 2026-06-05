from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_limit: int = Field(default=10, ge=1, le=200)
    max_categories: int = Field(default=50, ge=1, le=5000)
    max_sample_values: int = Field(default=20, ge=0, le=200)
    categorical_ratio_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    numeric_buckets: int = Field(default=5, ge=1, le=50)

