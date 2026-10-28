"""Small capability-based contracts for external music data providers."""

from typing import Protocol, runtime_checkable

from musicforge.models import Artist, Identifier, Recording, Release, Statistic


@runtime_checkable
class MusicSearchIf(Protocol):
    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        """Find recordings matching an artist and title."""
        ...


@runtime_checkable
class MusicMetadataIf(Protocol):
    async def get_recording(self, identifier: Identifier) -> Recording | None:
        """Retrieve a recording by a provider-scoped identifier."""
        ...

    async def get_release(self, identifier: Identifier) -> Release | None:
        """Retrieve a release by a provider-scoped identifier."""
        ...


@runtime_checkable
class MusicStatisticsIf(Protocol):
    async def get_statistics(self, identifier: Identifier) -> list[Statistic]:
        """Return statistics with source and metric semantics preserved."""
        ...


@runtime_checkable
class MusicDiscoveryIf(Protocol):
    async def related_artists(self, identifier: Identifier) -> list[Artist]:
        """Find artists related to the given artist identifier."""
        ...
