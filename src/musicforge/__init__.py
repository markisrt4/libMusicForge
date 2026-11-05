"""libMusicForge public Python API."""

from musicforge.core import MusicForge
from musicforge.models import Artist, Identifier, Recording, Release, Statistic
from musicforge.playback import (
    MusicBrainzNameResolver,
    PlaybackSourceIf,
    RecordingResolverIf,
    ResolutionResult,
    TrackIdentity,
)

__all__ = [
    "Artist",
    "Identifier",
    "MusicBrainzNameResolver",
    "MusicForge",
    "PlaybackSourceIf",
    "Recording",
    "RecordingResolverIf",
    "Release",
    "ResolutionResult",
    "Statistic",
    "TrackIdentity",
]
