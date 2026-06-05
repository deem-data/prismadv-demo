from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from prismadv.api.v1.schemas import (
    ColumnStatsResponse,
    Dataset,
    DatasetPreviewResponse,
    DatasetQualityResponse,
)


class ProfileBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: Dataset
    preview: DatasetPreviewResponse
    column_stats: dict[str, ColumnStatsResponse]
    quality: DatasetQualityResponse

