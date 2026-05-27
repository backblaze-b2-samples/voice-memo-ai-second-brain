"""Admin routes for the tagging pipeline (re-run)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.service import tagging as tagging_service
from app.service.memos import MemoKeyError, validate_memo_key

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/memos/{key:path}/retag")
async def retag_endpoint(key: str, background_tasks: BackgroundTasks):
    """Re-queue the tagging pipeline for a memo whose transcript exists."""
    try:
        validate_memo_key(key)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    background_tasks.add_task(tagging_service.run, key)
    logger.info("Tagging enqueued: key=%s", key)
    return {"enqueued": True, "key": key}
