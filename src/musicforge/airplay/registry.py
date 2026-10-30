"""Station source registry and deterministic metadata-source selection.

A source is eligible only when explicitly configured and verified. Health-based
selection does not itself start/stop collectors or invent fallback endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from .health import SourceStatus


class SourceKind(str, Enum):
    ICY = "icy"
    HLS = "hls"
    PLAYLIST = "playlist"


@dataclass(frozen=True)
class RadioSource:
    name: str
    kind: SourceKind
    url: str
    priority: int = 100
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("source name is required")
        if self.priority < 0:
            raise ValueError("priority must be nonnegative")
        url = urlparse(self.url)
        if url.scheme not in ("https", "http") or not url.netloc:
            raise ValueError("source URL must be HTTP(S)")


@dataclass(frozen=True)
class RadioStation:
    callsign: str
    sources: tuple[RadioSource, ...]

    def __post_init__(self) -> None:
        if not self.callsign.strip():
            raise ValueError("station callsign is required")
        if len({s.name for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate source names")


@dataclass(frozen=True)
class SourceSelection:
    station: str
    source: RadioSource | None
    reason: str


def choose_source(
    station: RadioStation,
    statuses: dict[str, SourceStatus] | None = None,
) -> SourceSelection:
    """Prefer a verified healthy source; never silently trust an untested URL.

    Unknown status is eligible for probing, but is lower priority than a
    known healthy source. NO_SONGS remains eligible: it can be talk programming.
    """
    statuses = statuses or {}
    eligible = [source for source in station.sources if source.verified]
    if not eligible:
        return SourceSelection(station.callsign, None, "no verified sources")
    ranked = []
    for source in eligible:
        status = statuses.get(source.name)
        if status in (SourceStatus.ERROR, SourceStatus.EMPTY_METADATA, SourceStatus.STALE):
            continue
        rank = 0 if status is SourceStatus.HEALTHY else (
            1 if status is SourceStatus.NO_SONGS else 2
        )
        ranked.append((rank, source.priority, source.name, source))
    if not ranked:
        return SourceSelection(station.callsign, None, "all verified sources unhealthy")
    selected = min(ranked, key=lambda item: item[:3])[3]
    return SourceSelection(station.callsign, selected, "verified source eligible")


# Initial seed is deliberately conservative: these endpoints were observed
# serving useful metadata; WRIF was observed serving empty ICY blocks.
DETROIT_STATIONS = (
    RadioStation("WNIC", (
        RadioSource("wnic-icy", SourceKind.ICY,
                    "https://stream.revma.ihrhls.com/zc1153?streamid=1153",
                    verified=True),
    )),
    RadioStation("WOMC", (
        RadioSource("womc-hls", SourceKind.HLS,
                    "https://live.amperwave.net/manifest/audacy-womcfmaac-hlsc.m3u8",
                    verified=True),
    )),
    RadioStation("WYCD", (
        RadioSource("wycd-hls", SourceKind.HLS,
                    "https://live.amperwave.net/manifest/audacy-wycdfmaac-hlsc.m3u8",
                    verified=True),
    )),
    RadioStation("WRIF", (
        RadioSource("wrif-icy", SourceKind.ICY,
                    "https://playerservices.streamtheworld.com/api/livestream-redirect/WRIFFMAACIHR.aac",
                    verified=False),
    )),
)
