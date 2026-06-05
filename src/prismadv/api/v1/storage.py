"""Session-isolated storage for uploaded files and generated results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prismadv.api.v1.schemas import CodeFile, Dataset
from prismadv.generation import GenerationContext


def _columns_match(a: list[str] | None, b: list[str] | None) -> bool:
    """Return True if two selected_columns values represent the same column set."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return sorted(a) == sorted(b)


@dataclass
class StoredFile:
    """Metadata for an uploaded file."""

    id: str
    name: str
    content: str | bytes
    size: int
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ColumnDetectionCache:
    """Cached column detection result for a (task_file, dataset) pair."""

    task_file_id: str
    dataset_id: str
    all_columns: list[str]
    accessed_columns: list[str]
    detection_cost: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GenerationJob:
    """Stored generation result."""

    id: str
    task_file_id: str
    dataset_id: str
    model: str | None = None  # LLM model used for generation
    selected_columns: list[str] | None = None  # Columns used for generation (None = LLM auto-detected)
    context: GenerationContext | None = None
    intermediate_result: dict | None = None  # Partial GenerationResult (serialized) for progressive UI
    status: str = "pending"  # pending, processing, completed, failed
    error: str | None = None
    progress: float = 0.0  # 0.0 to 1.0
    current_step: str = "Initializing..."  # Human-readable current step
    cancelled: bool = False  # Set to True to request cancellation
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SessionStorage:
    """Storage for a single session."""

    def __init__(self, session_id: str):
        """Initialize session storage.

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id
        self.files: dict[str, StoredFile] = {}
        self.jobs: dict[str, GenerationJob] = {}
        self._column_detections: list[ColumnDetectionCache] = []
        self.benchmark_jobs: dict[str, dict] = {}

    def store_file(self, name: str, content: str | bytes, metadata: dict[str, Any] | None = None) -> str:
        """Store a file and return its ID.

        Args:
            name: File name
            content: File content (text or bytes)
            metadata: Optional metadata

        Returns:
            File ID
        """
        file_id = str(uuid.uuid4())
        stored_file = StoredFile(
            id=file_id,
            name=name,
            content=content,
            size=len(content) if isinstance(content, (str, bytes)) else 0,
            metadata=metadata or {},
        )
        self.files[file_id] = stored_file
        return file_id

    def get_file(self, file_id: str) -> StoredFile | None:
        """Get file by ID.

        Args:
            file_id: File identifier

        Returns:
            StoredFile if found, None otherwise
        """
        return self.files.get(file_id)

    def store_job(
        self,
        task_file_id: str,
        dataset_id: str,
        model: str | None = None,
        selected_columns: list[str] | None = None,
    ) -> str:
        """Create a generation job.

        Args:
            task_file_id: Task file identifier
            dataset_id: Dataset identifier
            model: LLM model name used for generation
            selected_columns: Columns used for generation (None = LLM auto-detected)

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = GenerationJob(
            id=job_id,
            task_file_id=task_file_id,
            dataset_id=dataset_id,
            model=model,
            selected_columns=selected_columns,
        )
        self.jobs[job_id] = job
        return job_id

    def find_completed_job(
        self,
        task_file_id: str,
        dataset_id: str,
        model: str | None = None,
        selected_columns: list[str] | None = None,
    ) -> GenerationJob | None:
        """Find a completed job matching the given parameters.

        This enables caching - if a job with the same task file, dataset,
        model, and selected columns already exists and completed successfully,
        we can reuse it.

        Args:
            task_file_id: Task file identifier
            dataset_id: Dataset identifier
            model: LLM model name (None matches any model)
            selected_columns: Columns used for generation; must match exactly
                (None matches only None, i.e. LLM-auto-detected runs)

        Returns:
            Matching completed GenerationJob if found, None otherwise
        """
        for job in self.jobs.values():
            if (
                job.status == "completed"
                and job.task_file_id == task_file_id
                and job.dataset_id == dataset_id
                and job.context is not None
            ):
                # If model is specified, it must match
                if model is not None and job.model != model:
                    continue
                # selected_columns must match exactly (order-independent)
                if not _columns_match(job.selected_columns, selected_columns):
                    continue
                return job
        return None

    def find_column_detection(
        self, task_file_id: str, dataset_id: str
    ) -> ColumnDetectionCache | None:
        """Return a cached column detection result for the given files, if any."""
        for entry in self._column_detections:
            if entry.task_file_id == task_file_id and entry.dataset_id == dataset_id:
                return entry
        return None

    def store_column_detection(
        self,
        task_file_id: str,
        dataset_id: str,
        all_columns: list[str],
        accessed_columns: list[str],
        detection_cost: float = 0.0,
    ) -> None:
        """Cache a column detection result, replacing any previous entry for the same files."""
        self._column_detections = [
            e for e in self._column_detections
            if not (e.task_file_id == task_file_id and e.dataset_id == dataset_id)
        ]
        self._column_detections.append(
            ColumnDetectionCache(
                task_file_id=task_file_id,
                dataset_id=dataset_id,
                all_columns=all_columns,
                accessed_columns=accessed_columns,
                detection_cost=detection_cost,
            )
        )

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a pending or processing job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancellation was requested, False if job not found or already terminal
        """
        job = self.jobs.get(job_id)
        if job is None or job.status not in ("pending", "processing"):
            return False
        job.cancelled = True
        return True

    def get_job(self, job_id: str) -> GenerationJob | None:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            GenerationJob if found, None otherwise
        """
        return self.jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        *,
        context: GenerationContext | None = None,
        intermediate_result: dict | None = None,
        status: str | None = None,
        error: str | None = None,
        progress: float | None = None,
        current_step: str | None = None,
    ) -> bool:
        """Update a generation job.

        Args:
            job_id: Job identifier
            context: Generation context result
            intermediate_result: Partial result dict for progressive UI updates
            status: Job status
            error: Error message if failed
            progress: Progress value 0.0 to 1.0
            current_step: Human-readable current step description

        Returns:
            True if job was updated, False if not found
        """
        job = self.jobs.get(job_id)
        if job is None:
            return False

        if context is not None:
            job.context = context
        if intermediate_result is not None:
            job.intermediate_result = intermediate_result
        if status is not None:
            job.status = status
        if error is not None:
            job.error = error
        if progress is not None:
            job.progress = progress
        if current_step is not None:
            job.current_step = current_step

        return True

    def list_jobs(self) -> list[GenerationJob]:
        """List all jobs in this session.

        Returns:
            List of GenerationJob objects
        """
        return list(self.jobs.values())


class StorageManager:
    """Manages session-isolated storage for all users."""

    def __init__(self):
        """Initialize storage manager."""
        self._storage: dict[str, SessionStorage] = {}

    def get_storage(self, session_id: str) -> SessionStorage:
        """Get or create storage for a session.

        Args:
            session_id: Session identifier

        Returns:
            SessionStorage instance
        """
        if session_id not in self._storage:
            self._storage[session_id] = SessionStorage(session_id)
        return self._storage[session_id]

    def delete_storage(self, session_id: str) -> bool:
        """Delete storage for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if storage was deleted, False if not found
        """
        return self._storage.pop(session_id, None) is not None

    def storage_count(self) -> int:
        """Get number of active session storages.

        Returns:
            Number of storages
        """
        return len(self._storage)
