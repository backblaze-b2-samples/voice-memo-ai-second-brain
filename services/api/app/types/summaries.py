from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SummaryWindow = Literal["daily", "weekly"]


class Summary(BaseModel):
    """An AI-generated rollup of memos in a date window.

    Persisted as markdown at `summaries/<YYYY>/<DD>.md` (daily) or
    `summaries/<YYYY>/W<WW>.md` (weekly). The Pydantic model carries the
    raw markdown plus enough metadata for the UI to render the summary
    list without re-fetching every artifact.
    """

    key: str
    window: SummaryWindow
    period: str  # e.g. "2026-05-26" or "2026-W21"
    markdown: str
    memo_count: int
    generated_at: datetime
    model: str | None = None


class SummaryListEntry(BaseModel):
    """A compact entry for the summaries list view."""

    key: str
    window: SummaryWindow
    period: str
    memo_count: int
    generated_at: datetime
