"""Source health classification, independent of transport and UI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceStatus(str, Enum):
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    EMPTY_METADATA = "empty_metadata"
    NO_SONGS = "no_songs"
    ERROR = "error"


@dataclass(frozen=True)
class SourceHealth:
    station: str
    status: SourceStatus
    blocks: int
    parsed: int
    changes: int
    seconds_connected: float
    detail: str = ""


def classify_icy_health(
    station: str, *, blocks: int, parsed: int, changes: int,
    seconds_connected: float, minimum_seconds: float = 90.0,
    error: str | None = None,
) -> SourceHealth:
    """Avoid declaring a station unhealthy before sufficient observation time.

    Parsed metadata without recognized songs is different from a silent feed.
    """
    if error:
        status = SourceStatus.ERROR
    elif seconds_connected < minimum_seconds or blocks == 0:
        status = SourceStatus.CONNECTING
    elif parsed == 0:
        status = SourceStatus.EMPTY_METADATA
    elif changes == 0:
        status = SourceStatus.NO_SONGS
    else:
        status = SourceStatus.HEALTHY
    return SourceHealth(station, status, blocks, parsed, changes,
                        seconds_connected, error or "")
