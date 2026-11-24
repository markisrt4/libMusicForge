"""! @brief Small capability-based contracts for external music data providers."""

from typing import Protocol, runtime_checkable

from musicforge.models import Artist, Identifier, Recording, Release, Statistic


@runtime_checkable
class MusicSearchIf(Protocol):
    """! @brief Recording search capability."""

    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        """! @brief Find recordings matching an artist and title.

        @param self Current instance.
        @param artist Artist name.
        @param title Track title.
        @return Matching recording candidates.
        """
        ...


@runtime_checkable
class MusicMetadataIf(Protocol):
    """! @brief Recording and release lookup capability."""

    async def get_recording(self, identifier: Identifier) -> Recording | None:
        """! @brief Retrieve a recording by a provider-scoped identifier.

        @param self Current instance.
        @param identifier Provider-scoped entity identifier.
        @return Recording, or None if not found.
        """
        ...

    async def get_release(self, identifier: Identifier) -> Release | None:
        """! @brief Retrieve a release by a provider-scoped identifier.

        @param self Current instance.
        @param identifier Provider-scoped entity identifier.
        @return Release, or None if not found.
        """
        ...


@runtime_checkable
class MusicStatisticsIf(Protocol):
    """! @brief Source-attributed statistics capability."""

    async def get_statistics(self, identifier: Identifier) -> list[Statistic]:
        """! @brief Return statistics with source and metric semantics preserved.

        @param self Current instance.
        @param identifier Provider-scoped entity identifier.
        @return Source-attributed metric observations.
        """
        ...


@runtime_checkable
class MusicDiscoveryIf(Protocol):
    """! @brief Related artist discovery capability."""

    async def related_artists(self, identifier: Identifier) -> list[Artist]:
        """! @brief Find artists related to the given artist identifier.

        @param self Current instance.
        @param identifier Provider-scoped entity identifier.
        @return Related artist candidates.
        """
        ...
