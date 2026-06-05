"""File upload endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from prismadv.api.v1 import dependencies
from prismadv.api.v1.schemas import CodeFile, CodeLanguage, Column, Dataset
from prismadv.api.v1.storage import SessionStorage
from prismadv.profiling import ProfilerBackend, get_profiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# Configuration
MAX_TASK_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DATASET_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_TASK_EXTENSIONS = {".py", ".sql"}
ALLOWED_DATASET_EXTENSIONS = {".csv"}


def detect_language(filename: str, content: str) -> CodeLanguage:
    """Detect code language from filename and content.

    Args:
        filename: File name
        content: File content

    Returns:
        Detected language
    """
    ext = Path(filename).suffix.lower()
    if ext == ".py":
        return CodeLanguage.PYTHON
    elif ext == ".sql":
        return CodeLanguage.SQL
    else:
        # Fallback: check content
        if "select" in content.lower() or "from" in content.lower():
            return CodeLanguage.SQL
        return CodeLanguage.PYTHON


@router.post("/task", response_model=CodeFile, status_code=201)
async def upload_task_file(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> CodeFile:
    """Upload task code file (Python or SQL).

    Args:
        file: Uploaded file
        name: Optional custom file name
        storage: Session storage

    Returns:
        CodeFile metadata

    Raises:
        HTTPException: If file validation fails
    """
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_TASK_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_TASK_EXTENSIONS)}",
        )

    # Read file content
    content_bytes = await file.read()
    content_size = len(content_bytes)

    # Validate file size
    if content_size > MAX_TASK_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_TASK_FILE_SIZE / 1024 / 1024:.1f} MB",
        )

    # Decode content
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 text",
        )

    # Use custom name or original filename
    file_name = name or file.filename or "untitled.py"

    # Detect language
    language = detect_language(file_name, content)

    # Store file
    file_id = storage.store_file(
        name=file_name,
        content=content,
        metadata={
            "language": language.value,
            "size": content_size,
        },
    )

    # Retrieve stored file for response
    stored_file = storage.get_file(file_id)
    if not stored_file:
        raise HTTPException(status_code=500, detail="Failed to store file")

    logger.info(f"Uploaded task file: {file_id} ({file_name}, {language.value})")

    return CodeFile(
        id=stored_file.id,
        name=stored_file.name,
        language=language,
        size=stored_file.size,
        content=str(stored_file.content),
        uploaded_at=stored_file.uploaded_at,
    )


@router.post("/dataset", response_model=Dataset, status_code=201)
async def upload_dataset_file(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> Dataset:
    """Upload CSV dataset file.

    This endpoint also profiles the dataset to extract column metadata.

    Args:
        file: Uploaded CSV file
        name: Optional custom dataset name
        storage: Session storage

    Returns:
        Dataset metadata with column information

    Raises:
        HTTPException: If file validation or profiling fails
    """
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_DATASET_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Must be CSV",
        )

    # Read file content
    content_bytes = await file.read()
    content_size = len(content_bytes)

    # Validate file size
    if content_size > MAX_DATASET_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_DATASET_SIZE / 1024 / 1024:.1f} MB",
        )

    # Decode content
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV file must be valid UTF-8 text",
        )

    # Validate CSV has content
    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="CSV file is empty",
        )

    # Use custom name or original filename
    file_name = name or file.filename or "dataset.csv"

    # Store file first
    file_id = storage.store_file(
        name=file_name,
        content=content,
        metadata={"size": content_size},
    )

    # Profile the dataset to get column info
    # Save to temporary file for profiler
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Use builtin profiler (no external dependencies)
        profiler = get_profiler(ProfilerBackend.BUILTIN)
        profile_result = profiler.profile_csv(
            tmp_path,
            dataset_id=file_id,
            dataset_name=file_name,
        )

        # Convert to API schema
        columns = [
            Column(
                name=col.name,
                type=col.type,
                inferred_type=col.inferred_type,
                nullable=col.nullable,
            )
            for col in profile_result.dataset.columns
        ]

        logger.info(
            f"Uploaded dataset: {file_id} ({file_name}, "
            f"{profile_result.dataset.row_count} rows, "
            f"{len(columns)} columns)"
        )

        return Dataset(
            id=file_id,
            name=file_name,
            size=content_size,
            row_count=profile_result.dataset.row_count,
            column_count=len(columns),
            columns=columns,
            uploaded_at=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(f"Failed to profile dataset {file_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to parse CSV file. Please check the file format.",
        )
    finally:
        # Clean up temp file
        import os

        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> CodeFile | Dataset:
    """Get file metadata by ID.

    Args:
        file_id: File ID
        storage: Session storage

    Returns:
        File metadata (CodeFile or Dataset)

    Raises:
        HTTPException: If file not found
    """
    file = storage.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_id}",
        )

    # Determine file type based on metadata and file extension
    # If file has columns metadata, it's a dataset
    if "columns" in file.metadata or file.name.endswith(".csv"):
        return Dataset(
            id=file_id,
            name=file.name,
            size=file.metadata.get("size", file.size),
            row_count=file.metadata.get("row_count", 0),
            column_count=file.metadata.get("column_count", len(file.metadata.get("columns", []))),
            columns=file.metadata.get("columns", []),
            uploaded_at=file.uploaded_at,
        )
    else:
        # Task file (code)
        content = file.content if isinstance(file.content, str) else file.content.decode("utf-8")

        # Get language from metadata or detect it
        language_str = file.metadata.get("language")
        if language_str:
            language = CodeLanguage(language_str)
        else:
            language = detect_language(file.name, content)

        return CodeFile(
            id=file_id,
            name=file.name,
            size=file.metadata.get("size", file.size),
            language=language,
            content=content,
            uploaded_at=file.uploaded_at,
        )
