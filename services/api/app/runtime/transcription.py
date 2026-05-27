"""Admin-style routes for the transcription pipeline.

The transcription stage is normally fired automatically by `runtime/upload.py`
after a successful upload. These routes let an operator re-trigger the run
from the UI (for a memo whose transcription failed) or seeded data from B2
that pre-dates the pipeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service import transcription as transcription_service
from app.service.memos import MemoKeyError, validate_memo_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/memos/{key:path}/transcribe")
async def retranscribe_endpoint(key: str, background_tasks: BackgroundTasks):
    """Re-queue the transcription pipeline for a memo."""
    try:
        validate_memo_key(key)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    background_tasks.add_task(transcription_service.run, key)
    logger.info("Transcription enqueued: key=%s", key)
    return {"enqueued": True, "key": key}
