"""Portable playback observations and conservative recording resolution.

Playback adapters live outside the core. A track observation is not proof of a
MusicBrainz recording identity, even when title and duration match.
"""

from dataclasses import dataclass
from typing import Protocol

from musicforge.models import Recording


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
    """! @brief Source of portable playback observations. """

    async def current_track(self) -> TrackIdentity | None:
        """!
        @brief Return the observed track when playback is available.
        @param self The playback source.
        @return The current track observation when available.
        """
        ...


class RecordingSearchIf(Protocol):
    """! @brief Recording search required by playback resolution. """

    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        """!
        @brief Search for recording candidates by artist and title.
        @param self The search provider.
        @param artist Artist name.
        @param title Recording title.
        @return Matching recording candidates.
        """
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
    """! @brief Conservative resolver for playback observations. """

    async def resolve(self, track: TrackIdentity) -> ResolutionResult:
        """!
        @brief Resolve an observation into recording candidates.
        @param self The resolver instance.
        @param track Observed playback identity.
        @return Resolution candidates and evidence.
        """
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
