"""Provider-attributed track comparisons.

Ratios describe Last.fm recorded listening, not global streaming popularity.
"""

from dataclasses import dataclass
from typing import Protocol, Sequence

from musicforge.models import Statistic


class TrackStatisticsIf(Protocol):
    async def track_statistics(self, artist: str, title: str) -> list[Statistic]: ...


@dataclass(frozen=True, slots=True)
class TrackComparison:
    artist: str
    title: str
    listeners: int | None
    scrobbles: int | None
    provider: str = "lastfm"

    @property
    def scrobbles_per_listener(self) -> float | None:
        if self.listeners is None or self.scrobbles is None or self.listeners == 0:
            return None
        return self.scrobbles / self.listeners


def _count(stats: Sequence[Statistic], metric: str) -> int | None:
    matches = [s for s in stats if s.provider == "lastfm" and s.metric == metric]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"Duplicate Last.fm metric: {metric}")
    value = matches[0].value
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid Last.fm count for {metric}")
    return value


async def compare_tracks(
    provider: TrackStatisticsIf,
    tracks: Sequence[tuple[str, str]],
    *,
    sort_by: str = "listeners",
    descending: bool = True,
) -> list[TrackComparison]:
    """Compare track totals from Last.fm.

    Uses sequential requests to avoid unnecessary API bursts. Missing values
    are kept as None, not silently converted to zero.
    """
    if sort_by not in {"listeners", "scrobbles", "ratio"}:
        raise ValueError("sort_by must be listeners, scrobbles, or ratio")
    results: list[TrackComparison] = []
    for artist, title in tracks:
        if not artist.strip() or not title.strip():
            raise ValueError("artist and title must not be empty")
        stats = await provider.track_statistics(artist, title)
        results.append(
            TrackComparison(
                artist=artist,
                title=title,
                listeners=_count(stats, "global_listener_count"),
                scrobbles=_count(stats, "global_scrobble_count"),
            )
        )

    def key(item: TrackComparison) -> tuple[bool, float]:
        value = (
            item.scrobbles_per_listener if sort_by == "ratio"
            else getattr(item, sort_by)
        )
        return (value is None, -(float(value)) if descending and value is not None else float(value or 0))

    return sorted(results, key=key)
