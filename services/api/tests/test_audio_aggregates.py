"""Tests for `service.memos.get_memo_aggregates`.

Aggregates feed the dashboard tiles (Total memos, Total duration, Pipeline
status breakdown). The function HEADs every memo in parallel to pull
durations stamped at upload time AND to derive transcription status. We
stub the three repo calls (`list_audio_objects`,
`head_audio_objects_parallel`, `head_transcript_status_parallel`) to
exercise the summation logic.
"""

from datetime import UTC, datetime

from app.service import memos as memos_service


def _audio_obj(key: str, size: int = 1234) -> dict:
    return {
        "Key": key,
        "Size": size,
        "LastModified": datetime(2026, 5, 22, tzinfo=UTC),
    }


def _patch_pipeline_status_empty(monkeypatch):
    monkeypatch.setattr(
        memos_service, "head_transcript_status_parallel", lambda keys: {}
    )


def test_aggregates_sum_duration_from_head_metadata(monkeypatch):
    """Real `total_duration_ms` is summed from `x-amz-meta-duration-ms`."""
    objs = [
        _audio_obj("audio/2026/05/a--abc.wav", size=1000),
        _audio_obj("audio/2026/05/b--def.mp3", size=2000),
        _audio_obj("audio/2026/05/c--ghi.flac", size=3000),
    ]
    heads = {
        "audio/2026/05/a--abc.wav": {"Metadata": {"duration-ms": "1000"}},
        "audio/2026/05/b--def.mp3": {"Metadata": {"duration-ms": "2500"}},
        "audio/2026/05/c--ghi.flac": {"Metadata": {"duration-ms": "500"}},
    }
    monkeypatch.setattr(
        memos_service, "list_audio_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        memos_service, "head_audio_objects_parallel", lambda keys: heads
    )
    _patch_pipeline_status_empty(monkeypatch)

    result = memos_service.get_memo_aggregates()

    assert result["total_memos"] == 3
    assert result["total_audio_assets"] == 3
    assert result["total_duration_ms"] == 4000
    assert result["total_size_bytes"] == 6000


def test_aggregates_format_counts_include_other_bucket(monkeypatch):
    """`formats` is keyed by extension; unknown extensions land in `other`."""
    objs = [
        _audio_obj("audio/2026/05/one--abc.wav"),
        _audio_obj("audio/2026/05/two--def.wav"),
        _audio_obj("audio/2026/05/three--ghi.mp3"),
        _audio_obj("audio/2026/05/four--jkl.flac"),
        # Externally-seeded file with no extension lands in the "other" bucket.
        _audio_obj("audio/legacy/noext"),
    ]
    monkeypatch.setattr(
        memos_service, "list_audio_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        memos_service, "head_audio_objects_parallel", lambda keys: {}
    )
    _patch_pipeline_status_empty(monkeypatch)

    result = memos_service.get_memo_aggregates()

    assert result["formats"] == {
        "wav": 2,
        "mp3": 1,
        "flac": 1,
        "other": 1,
    }


def test_aggregates_handle_objects_without_stamped_metadata(monkeypatch):
    """Externally-seeded objects (no `x-amz-meta-*`) contribute 0 ms but
    still count toward `total_memos` and `formats`."""
    objs = [
        # Stamped: contributes 7500 ms.
        _audio_obj("audio/2026/05/stamped--abc.wav", size=500),
        # Externally seeded: no head response at all.
        _audio_obj("audio/legacy/seed.wav", size=100),
        # HEAD returned, but no Metadata block — still 0 ms.
        _audio_obj("audio/legacy/empty-meta.mp3", size=200),
    ]
    heads = {
        "audio/2026/05/stamped--abc.wav": {"Metadata": {"duration-ms": "7500"}},
        "audio/legacy/empty-meta.mp3": {"Metadata": {}},
        # `audio/legacy/seed.wav` deliberately omitted to simulate a HEAD miss.
    }
    monkeypatch.setattr(
        memos_service, "list_audio_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        memos_service, "head_audio_objects_parallel", lambda keys: heads
    )
    _patch_pipeline_status_empty(monkeypatch)

    result = memos_service.get_memo_aggregates()

    assert result["total_memos"] == 3
    assert result["total_duration_ms"] == 7500
    assert result["total_size_bytes"] == 800
    assert result["formats"] == {"wav": 2, "mp3": 1}


def test_aggregates_empty_bucket_returns_zeros(monkeypatch):
    """No objects -> zero everything, empty formats dict, no HEAD fanout."""
    head_calls: list[list[str]] = []

    def _head(keys):
        head_calls.append(list(keys))
        return {}

    monkeypatch.setattr(memos_service, "list_audio_objects", lambda max_keys: [])
    monkeypatch.setattr(memos_service, "head_audio_objects_parallel", _head)
    monkeypatch.setattr(
        memos_service, "head_transcript_status_parallel", _head
    )

    result = memos_service.get_memo_aggregates()

    assert result["total_memos"] == 0
    assert result["total_duration_ms"] == 0
    assert result["total_size_bytes"] == 0
    assert result["formats"] == {}
    # Skip the HEAD fanout entirely when there's nothing to head.
    assert head_calls == []


def test_aggregates_breaks_down_pipeline_status(monkeypatch):
    """`transcribed_count` / `pending_count` / `failed_count` derive from
    `head_transcript_status_parallel`."""
    objs = [
        _audio_obj("audio/2026/05/done--1.wav"),
        _audio_obj("audio/2026/05/done--2.wav"),
        _audio_obj("audio/2026/05/wait--3.wav"),
        _audio_obj("audio/2026/05/oops--4.wav"),
    ]
    statuses = {
        "audio/2026/05/done--1.wav": "transcribed",
        "audio/2026/05/done--2.wav": "transcribed",
        "audio/2026/05/wait--3.wav": "pending",
        "audio/2026/05/oops--4.wav": "failed",
    }
    monkeypatch.setattr(
        memos_service, "list_audio_objects", lambda max_keys: objs
    )
    monkeypatch.setattr(
        memos_service, "head_audio_objects_parallel", lambda keys: {}
    )
    monkeypatch.setattr(
        memos_service,
        "head_transcript_status_parallel",
        lambda keys: statuses,
    )

    result = memos_service.get_memo_aggregates()

    assert result["transcribed_count"] == 2
    assert result["pending_count"] == 1
    assert result["failed_count"] == 1
