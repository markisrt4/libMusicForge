"""Diagnostics for HLS playlist coverage and repeated segment observations."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit
from datetime import datetime

from .hls import HlsPlaylist, HlsSegment


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
    """Emit candidate song changes across overlapping HLS playlist snapshots.

    Keeps per-station continuity and ignores previously processed segments.
    This is not an authoritative play counter: missing playlist intervals,
    metadata errors and station breaks can conceal transitions.
    """

    def __init__(self) -> None:
        self._last_title: dict[str, str | None] = {}
        self._last_position: dict[str, tuple[datetime | None, int]] = {}

    def observe(self, station: str, playlist: HlsPlaylist) -> tuple[HlsSegment, ...]:
        observations: list[HlsSegment] = []
        last_title = self._last_title.get(station)
        last_position = self._last_position.get(station)

        for segment in playlist.segments:
            position = (segment.started_at, segment.sequence)
            if last_position is not None:
                prior_time, prior_sequence = last_position
                if segment.started_at is not None and prior_time is not None:
                    if segment.started_at <= prior_time:
                        continue
                elif segment.sequence <= prior_sequence:
                    continue

            title = segment.title.strip()
            if not title or urlsplit(title).scheme.lower() in ("http", "https") or " - " not in title:
                # Unknown/ad segments do not prove the current song ended.
                # Preserve last known song until a different valid title arrives.
                pass
            else:
                if title != last_title:
                    observations.append(segment)
                last_title = title
            last_position = position

        self._last_title[station] = last_title
        if last_position is not None:
            self._last_position[station] = last_position
        return tuple(observations)
