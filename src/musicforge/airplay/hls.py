"""Parse HLS media playlists for candidate airplay observations.

EXTINF titles describe segments, not guaranteed song boundaries. This module
deliberately emits observations, not authoritative play-count events.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit


@dataclass(frozen=True)
class HlsSegment:
    sequence: int
    duration_seconds: float
    title: str
    started_at: datetime | None


@dataclass(frozen=True)
class HlsPlaylist:
    segments: tuple[HlsSegment, ...]
    target_duration_seconds: int | None

    @property
    def duration_seconds(self) -> float:
        return sum(segment.duration_seconds for segment in self.segments)

    @property
    def timestamped_duration_seconds(self) -> float:
        return sum(s.duration_seconds for s in self.segments if s.started_at is not None)


def parse_media_playlist(text: str) -> HlsPlaylist:
    """Parse segment titles and program timestamps, without fetching media."""
    if not text.lstrip().startswith("#EXTM3U"):
        raise ValueError("Not an HLS playlist")
    if "#EXT-X-STREAM-INF:" in text:
        raise ValueError("Expected media playlist, got master playlist")
    sequence = 0
    target: int | None = None
    clock: datetime | None = None
    pending: tuple[float, str] | None = None
    segments: list[HlsSegment] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            sequence = int(line.partition(":")[2])
        elif line.startswith("#EXT-X-TARGETDURATION:"):
            target = int(line.partition(":")[2])
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            clock = datetime.fromisoformat(line.partition(":")[2].replace("Z", "+00:00"))
        elif line.startswith("#EXTINF:"):
            duration, sep, title = line.partition(":")[2].partition(",")
            if not sep:
                raise ValueError("Malformed EXTINF")
            pending = (float(duration), title.strip())
        elif line and not line.startswith("#"):
            if pending is None:
                continue
            duration, title = pending
            segments.append(HlsSegment(sequence, duration, title, clock))
            sequence += 1
            if clock is not None:
                clock += timedelta(seconds=duration)
            pending = None
    return HlsPlaylist(tuple(segments), target)


def song_observations(playlist: HlsPlaylist) -> tuple[HlsSegment, ...]:
    """Return distinct consecutive plausible song labels within one playlist.

    Excludes empty titles and URL-shaped ad/banner descriptions. Other
    non-music text can still appear; caller must classify before counting.
    """
    found: list[HlsSegment] = []
    last_title: str | None = None
    for segment in playlist.segments:
        title = segment.title
        if not title or urlsplit(title).scheme.lower() in ("http", "https"):
            last_title = None
            continue
        if " - " not in title:
            last_title = None
            continue
        if title != last_title:
            found.append(segment)
        last_title = title
    return tuple(found)
