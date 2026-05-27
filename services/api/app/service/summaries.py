"""AI summary generation.

Aggregates transcripts in a date window, sends them to the chat model, and
caches the resulting markdown in B2. Re-requests for the same period
return the cached markdown rather than re-billing the chat API.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from app.config import settings
from app.repo import (
    daily_summary_key,
    get_summary,
    get_transcript,
    list_audio_objects,
    list_summary_sidecars,
    put_summary,
    weekly_summary_key,
)
from app.repo.llm_client import LlmClientError, chat_completion
from app.types import Summary, SummaryListEntry, SummaryWindow

logger = logging.getLogger(__name__)

# Cap the bundle of transcripts we send to the model per summary. The
# chat-model token budget is the limit; we trim aggressively because
# voice memos are usually short.
MAX_BUNDLE_CHARS = 24_000

SYSTEM_PROMPT = (
    "You write concise daily/weekly journal summaries from voice-memo "
    "transcripts. Produce markdown with: a one-line lede, a `Highlights` "
    "section (3-5 bullets), an `Open threads` section (1-3 bullets, only "
    "if any), and an italicized one-line meta footer with the memo count. "
    "Do NOT invent details that aren't in the transcripts."
)


def _iso_week(today: date) -> tuple[int, int]:
    cal = today.isocalendar()
    return cal.year, cal.week


def _build_bundle(transcripts: list[dict]) -> str:
    parts: list[str] = []
    running = 0
    for t in transcripts:
        text = str(t.get("text", "")).strip()
        if not text:
            continue
        when = t.get("generated_at") or ""
        block = f"---\n[{when}] {t.get('memo_key', '')}\n{text}\n"
        running += len(block)
        if running > MAX_BUNDLE_CHARS:
            break
        parts.append(block)
    return "\n".join(parts)


def _memos_in_window(start: date, end: date) -> list[str]:
    """Return memo keys whose `LastModified` falls in [start, end]."""
    raw = list_audio_objects(max_keys=10_000)
    return [
        obj["Key"]
        for obj in raw
        if start <= obj["LastModified"].date() <= end
    ]


def _load_transcripts(memo_keys: list[str]) -> list[dict]:
    out: list[dict] = []
    for key in memo_keys:
        t = get_transcript(key)
        if t:
            out.append(t)
    return out


def _summary_key_for(window: SummaryWindow, period: str) -> str:
    """Period strings: `YYYY-MM-DD` for daily, `YYYY-Www` for weekly."""
    if window == "daily":
        year = int(period.split("-", 1)[0])
        return daily_summary_key(year, period)
    year_str, week_str = period.split("-W", 1)
    return weekly_summary_key(int(year_str), int(week_str))


def _window_dates(window: SummaryWindow, period: str) -> tuple[date, date]:
    if window == "daily":
        d = date.fromisoformat(period)
        return d, d
    year_str, week_str = period.split("-W", 1)
    year, week = int(year_str), int(week_str)
    # ISO week starts on Monday.
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def generate_summary(
    window: SummaryWindow, period: str, force: bool = False
) -> Summary:
    """Generate (or return cached) summary markdown for `period`."""
    summary_key = _summary_key_for(window, period)
    if not force:
        markdown, sidecar = get_summary(summary_key)
        if markdown and sidecar:
            return Summary(
                key=summary_key,
                window=window,
                period=period,
                markdown=markdown,
                memo_count=int(sidecar.get("memo_count", 0)),
                generated_at=datetime.fromisoformat(
                    sidecar["generated_at"]
                ),
                model=sidecar.get("model"),
            )

    start, end = _window_dates(window, period)
    memo_keys = _memos_in_window(start, end)
    transcripts = _load_transcripts(memo_keys)
    if not transcripts:
        markdown = (
            f"# {window.title()} summary — {period}\n\n"
            "_No transcribed memos in this window yet._\n"
        )
    else:
        bundle = _build_bundle(transcripts)
        try:
            markdown = chat_completion(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Window: {window} ({period})\n"
                            f"Memo count: {len(transcripts)}\n\n"
                            f"Transcripts:\n{bundle}"
                        ),
                    },
                ],
                temperature=0.3,
            )
        except LlmClientError as e:
            logger.warning("Summary generation failed: %s", e)
            raise

    sidecar = {
        "key": summary_key,
        "window": window,
        "period": period,
        "memo_count": len(transcripts),
        "generated_at": datetime.now(UTC).isoformat(),
        "model": settings.openai_chat_model,
    }
    put_summary(summary_key, markdown, sidecar)
    return Summary(
        key=summary_key,
        window=window,
        period=period,
        markdown=markdown,
        memo_count=len(transcripts),
        generated_at=datetime.now(UTC),
        model=settings.openai_chat_model,
    )


def list_summaries() -> list[SummaryListEntry]:
    """Return every previously-generated summary, newest-first."""
    sidecars = list_summary_sidecars()
    entries: list[SummaryListEntry] = []
    for s in sidecars:
        try:
            entries.append(
                SummaryListEntry(
                    key=s["key"],
                    window=s["window"],
                    period=s["period"],
                    memo_count=int(s.get("memo_count", 0)),
                    generated_at=datetime.fromisoformat(s["generated_at"]),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    entries.sort(key=lambda e: e.generated_at, reverse=True)
    return entries
