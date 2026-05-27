import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.repo import get_tags, get_transcript
from app.service.memos import (
    MemoKeyError,
    MemoNotFound,
    bulk_delete_memos,
    delete_memo,
    get_download_url,
    get_playback_url,
    list_memos,
)
from app.service.related_memos import find_related
from app.types import Memo, RelatedMemo, Transcript


class BulkDeleteRequest(BaseModel):
    keys: list[str] = Field(..., min_length=1, max_length=1000)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/memos", response_model=list[Memo])
async def list_memos_endpoint(limit: int = 100):
    """List voice memos with their derived pipeline status."""
    try:
        return list_memos(limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/memos/bulk-delete")
async def bulk_delete_memos_endpoint(body: BulkDeleteRequest):
    """Delete up to 1000 memos (and their sibling artifacts) in one request."""
    try:
        deleted, errors = bulk_delete_memos(body.keys)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete memos") from None
    logger.info(
        "Bulk memo delete: requested=%d deleted=%d errors=%d",
        len(body.keys),
        len(deleted),
        len(errors),
    )
    return {"deleted": deleted, "errors": errors}


@router.get("/memos/{key:path}/playback")
async def playback_endpoint(key: str):
    try:
        url = get_playback_url(key)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except MemoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}


@router.get("/memos/{key:path}/download")
async def download_endpoint(key: str):
    try:
        url = get_download_url(key)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except MemoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url, "expires_in": 600}


@router.get("/memos/{key:path}/transcript", response_model=Transcript | None)
async def transcript_endpoint(key: str):
    payload = get_transcript(key)
    if payload is None:
        raise HTTPException(status_code=404, detail="Transcript not available yet")
    return payload


@router.get("/memos/{key:path}/tags")
async def tags_endpoint(key: str):
    payload = get_tags(key)
    if payload is None:
        return {"memo_key": key, "tags": [], "topics": [], "entities": []}
    return payload


@router.get(
    "/memos/{key:path}/related", response_model=list[RelatedMemo]
)
async def related_endpoint(key: str, top_k: int = 5):
    if top_k < 1 or top_k > 25:
        raise HTTPException(status_code=400, detail="top_k must be 1..25")
    try:
        return find_related(key, top_k=top_k)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.delete("/memos/{key:path}")
async def delete_endpoint(key: str):
    try:
        delete_memo(key)
    except MemoKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete memo") from None
    logger.info("Memo deleted: key=%s", key)
    return {"deleted": True, "key": key}
