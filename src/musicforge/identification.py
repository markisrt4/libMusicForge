"""Cross-provider lookup with explicit, non-authoritative name matching.

MusicBrainz identifies candidate recordings; Last.fm statistics are looked up
by artist/title, not by MusicBrainz recording ID. No identity equivalence is
claimed or inferred.
"""

from dataclasses import dataclass
from typing import Protocol

from musicforge.models import Recording, Statistic


class RecordingSearchIf(Protocol):
    async def search_recordings(self, artist: str, title: str) -> list[Recording]: ...


class TrackStatisticsIf(Protocol):
    async def track_statistics(self, artist: str, title: str) -> list[Statistic]: ...


@dataclass(frozen=True, slots=True)
class EnrichedTrack:
    requested_artist: str
    requested_title: str
    candidates: tuple[Recording, ...]
    statistics: tuple[Statistic, ...]
    match_method: str = "artist_title_lookup"
    verified_recording_match: bool = False
    metadata_error: str | None = None
    statistics_error: str | None = None


async def identify_and_enrich(
    metadata: RecordingSearchIf,
    statistics: TrackStatisticsIf,
    artist: str,
    title: str,
) -> EnrichedTrack:
    """Retrieve MusicBrainz candidates and independent Last.fm track metrics.

    Results deliberately retain *all* recording candidates. Last.fm totals
    are associated with the artist/title query, never with an individual
    MusicBrainz recording or release.
    """
    if not artist.strip() or not title.strip():
        raise ValueError("artist and title must be nonempty")
    # Provider failures are independent; preserve successful partial results.
    candidates: list[Recording] = []
    stats: list[Statistic] = []
    metadata_error: str | None = None
    statistics_error: str | None = None
    try:
        candidates = await metadata.search_recordings(artist, title)
    except Exception as exc:
        metadata_error = f"{type(exc).__name__}: {exc}"
    try:
        stats = await statistics.track_statistics(artist, title)
    except Exception as exc:
        statistics_error = f"{type(exc).__name__}: {exc}"
    return EnrichedTrack(
        requested_artist=artist,
        requested_title=title,
        candidates=tuple(candidates),
        statistics=tuple(stats),
        metadata_error=metadata_error,
        statistics_error=statistics_error,
    )
