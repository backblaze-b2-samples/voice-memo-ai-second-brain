import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile

from app.config import settings
from app.runtime.metrics import record_upload
from app.service import transcription as transcription_service
from app.service.audio_metadata import AUDIO_MIME_TYPES
from app.service.upload import UploadError, process_upload
from app.types import FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_audio(content_type: str) -> bool:
    return content_type in AUDIO_MIME_TYPES or content_type.startswith("audio/")


@router.post("/upload", response_model=FileUploadResponse)
async def upload(
    request: Request, file: UploadFile, background_tasks: BackgroundTasks
):
    content_type = file.content_type or "application/octet-stream"
    content_length_header = request.headers.get("content-length")
    content_length = int(content_length_header) if content_length_header else None

    # Read file with chunked streaming and early size rejection
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    file_data = b"".join(chunks)

    try:
        result = process_upload(
            file_data=file_data,
            filename=file.filename or "",
            content_type=content_type,
            content_length=content_length,
        )
    except UploadError as e:
        logger.warning("Upload rejected: %s", e.detail)
        record_upload(success=False)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    record_upload(success=True)
    logger.info(
        "Memo uploaded: key=%s size=%d type=%s",
        result.key,
        result.size_bytes,
        result.content_type,
    )

    # Fan out the pipeline for audio uploads only — non-audio files land
    # in `uploads/` and skip transcription. The transcription stage in
    # turn fans out to tagging + embeddings on success.
    if _is_audio(content_type):
        background_tasks.add_task(transcription_service.run, result.key)

    return result


# Alternative MediaRecorder-friendly endpoint. Mirrors `/upload` so future
# iOS Shortcuts / Android Tasker recipes that target a memo-specific URL
# don't need conditional logic. Documented in
# `docs/features/memo-capture.md`.
@router.post("/memos", response_model=FileUploadResponse)
async def post_memo(
    request: Request, file: UploadFile, background_tasks: BackgroundTasks
):
    return await upload(request, file, background_tasks)
