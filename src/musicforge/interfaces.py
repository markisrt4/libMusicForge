"""Small capability-based contracts for external music data providers."""

from typing import Protocol, runtime_checkable

from musicforge.models import Artist, Identifier, Recording, Release, Statistic


@runtime_checkable
class MusicSearchIf(Protocol):
    """! @brief Search capability for external music providers. """

    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        """!
        @brief Find recordings matching an artist and title.
        @param self The provider instance.
        @param artist Artist name to search for.
        @param title Recording title to search for.
        @return Matching recording candidates.
        """
        ...


@runtime_checkable
class MusicMetadataIf(Protocol):
    """! @brief Metadata retrieval capability for external music providers. """

    async def get_recording(self, identifier: Identifier) -> Recording | None:
        """!
        @brief Retrieve a recording by a provider-scoped identifier.
        @param self The provider instance.
        @param identifier Provider-scoped recording identifier.
        @return The recording when found.
        """
        ...

    async def get_release(self, identifier: Identifier) -> Release | None:
        """!
        @brief Retrieve a release by a provider-scoped identifier.
        @param self The provider instance.
        @param identifier Provider-scoped release identifier.
        @return The release when found.
        """
        ...


@runtime_checkable
class MusicStatisticsIf(Protocol):
    """! @brief Statistics capability for external music providers. """

    async def get_statistics(self, identifier: Identifier) -> list[Statistic]:
        """!
        @brief Return statistics with source and metric semantics preserved.
        @param self The provider instance.
        @param identifier Provider-scoped subject identifier.
        @return Provider-attributed statistics.
        """
        ...


@runtime_checkable
class MusicDiscoveryIf(Protocol):
    """! @brief Related-music discovery capability for external providers. """

    async def related_artists(self, identifier: Identifier) -> list[Artist]:
        """!
        @brief Find artists related to the given artist identifier.
        @param self The provider instance.
        @param identifier Provider-scoped artist identifier.
        @return Related artist candidates.
        """
        ...
