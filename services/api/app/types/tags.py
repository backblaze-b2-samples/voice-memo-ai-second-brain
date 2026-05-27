from datetime import datetime

from pydantic import BaseModel


class MemoTags(BaseModel):
    """LLM-extracted tags/topics/entities for a single memo.

    Persisted at `tags/<YYYY>/<MM>/<stem>.json` in B2. Each list is normalized
    to lowercase by the service layer at write time so downstream chip
    rendering is case-stable.
    """

    memo_key: str
    tags: list[str] = []
    topics: list[str] = []
    entities: list[str] = []
    model: str | None = None
    generated_at: datetime


class RelatedMemo(BaseModel):
    """One entry in the cross-reference response for `/memos/{key}/related`."""

    key: str
    score: float
    title_preview: str | None = None
    transcript_preview: str | None = None
