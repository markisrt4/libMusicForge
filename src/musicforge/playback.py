"""Portable playback observations and conservative recording resolution.

Playback adapters live outside the core. A track observation is not proof of a
MusicBrainz recording identity, even when title and duration match.
"""

from dataclasses import dataclass
from typing import Protocol

from musicforge.models import Identifier, Recording


@dataclass(frozen=True, slots=True)
class TrackIdentity:
    source: str
    title: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    isrc: str | None = None
    source_track_id: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.title.strip() or not self.artist.strip():
            raise ValueError("source, title and artist must be nonempty")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must not be negative")


class PlaybackSourceIf(Protocol):
    async def current_track(self) -> TrackIdentity | None:
        """Return the observed track, or None when playback is unavailable."""
        ...


class RecordingSearchIf(Protocol):
    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        ...


@dataclass(frozen=True, slots=True)
class RecordingCandidate:
    recording: Recording
    evidence: tuple[str, ...]
    duration_difference_ms: int | None


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    observed: TrackIdentity
    candidates: tuple[RecordingCandidate, ...]
    verified: bool = False


class RecordingResolverIf(Protocol):
    async def resolve(self, track: TrackIdentity) -> ResolutionResult:
        ...


class MusicBrainzNameResolver:
    """Search by name and annotate evidence without asserting identity.

    ISRC resolution is deliberately not claimed or attempted here.
    """

    def __init__(self, search: RecordingSearchIf) -> None:
        self._search = search

    async def resolve(self, track: TrackIdentity) -> ResolutionResult:
        recordings = await self._search.search_recordings(track.artist, track.title)
        candidates: list[RecordingCandidate] = []
        for recording in recordings:
            evidence: list[str] = []
            if recording.title.casefold() == track.title.casefold():
                evidence.append("exact_title")
            if any(a.name.casefold() == track.artist.casefold() for a in recording.artists):
                evidence.append("exact_artist_credit")
            delta = None
            if track.duration_ms is not None and recording.duration_ms is not None:
                delta = abs(track.duration_ms - recording.duration_ms)
                if delta <= 2000:
                    evidence.append("duration_within_2s")
            candidates.append(RecordingCandidate(recording, tuple(evidence), delta))
        return ResolutionResult(observed=track, candidates=tuple(candidates))
