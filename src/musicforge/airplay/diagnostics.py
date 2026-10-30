"""Diagnostics for HLS playlist coverage and repeated segment observations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .hls import HlsPlaylist, HlsSegment, song_observations


@dataclass(frozen=True)
class PlaylistDiagnostics:
    media_duration_seconds: float
    wall_span_seconds: float | None
    gaps_seconds: tuple[float, ...]
    overlaps_seconds: tuple[float, ...]


def diagnose_playlist(playlist: HlsPlaylist) -> PlaylistDiagnostics:
    """Compare segment timestamps against the preceding segment's end."""
    gaps: list[float] = []
    overlaps: list[float] = []
    previous: HlsSegment | None = None
    for segment in playlist.segments:
        if previous and previous.started_at and segment.started_at:
            delta = (segment.started_at - previous.started_at).total_seconds()
            difference = delta - previous.duration_seconds
            if difference > 0.05:
                gaps.append(difference)
            elif difference < -0.05:
                overlaps.append(-difference)
        previous = segment
    stamped = [s for s in playlist.segments if s.started_at is not None]
    span = None
    if stamped:
        first, last = stamped[0], stamped[-1]
        assert first.started_at is not None and last.started_at is not None
        span = (last.started_at - first.started_at).total_seconds() + last.duration_seconds
    return PlaylistDiagnostics(playlist.duration_seconds, span, tuple(gaps), tuple(overlaps))


class HlsObservationTracker:
    """Deduplicate segment observations across overlapping playlist snapshots.

    This is NOT a play counter: same song across separate sequences may be
    the same continuous play, and titles can include non-music material.
    """
    def __init__(self) -> None:
        self._seen: set[tuple[str, int, datetime | None, str]] = set()

    def observe(self, station: str, playlist: HlsPlaylist) -> tuple[HlsSegment, ...]:
        observations: list[HlsSegment] = []
        for segment in song_observations(playlist):
            key = (station, segment.sequence, segment.started_at, segment.title)
            if key not in self._seen:
                observations.append(segment)
                self._seen.add(key)
        return tuple(observations)
