"""Daily/weekly AI summary routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.repo.llm_client import LlmClientError
from app.service import summaries as summaries_service
from app.types import Summary, SummaryListEntry

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateSummaryRequest(BaseModel):
    window: Literal["daily", "weekly"] = "daily"
    period: str | None = None  # ISO date `YYYY-MM-DD` or ISO week `YYYY-Www`
    force: bool = False


def _default_period(window: str) -> str:
    today = datetime.now(UTC).date()
    if window == "daily":
        return today.isoformat()
    cal = today.isocalendar()
    return f"{cal.year}-W{cal.week:02d}"


@router.get("/summaries", response_model=list[SummaryListEntry])
async def list_summaries_endpoint():
    return summaries_service.list_summaries()


@router.get("/summaries/{window}/{period}", response_model=Summary)
async def get_summary_endpoint(window: Literal["daily", "weekly"], period: str):
    """Return the cached summary for `period` (does NOT generate on miss)."""
    try:
        summary = summaries_service.generate_summary(window, period, force=False)
    except LlmClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    return summary


@router.post("/summaries/generate", response_model=Summary)
async def generate_summary_endpoint(body: GenerateSummaryRequest):
    """Generate (or regenerate when `force=True`) a daily/weekly summary."""
    period = body.period or _default_period(body.window)
    try:
        summary = summaries_service.generate_summary(
            body.window, period, force=body.force
        )
    except LlmClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    logger.info(
        "Summary generated: window=%s period=%s memos=%d",
        body.window,
        period,
        summary.memo_count,
    )
    return summary
