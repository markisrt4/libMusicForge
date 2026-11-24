"""! @brief Minimal orchestration entry point for music provider capabilities."""

from collections.abc import Iterable
from typing import Self

from musicforge.interfaces import MusicSearchIf
from musicforge.models import Recording


class MusicForge:
    """! @brief Library entry point. Providers are optional and independently configured."""

    def __init__(self, providers: Iterable[object] = ()) -> None:
        """! @brief Initialize the configured instance.

        @param self Current instance.
        @param providers Independently configured providers.
        """
        self._providers = tuple(providers)

    async def __aenter__(self) -> Self:
        """! @brief Enter the asynchronous context.

        @param self Current instance.
        @return Current instance.
        """
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        """! @brief Exit the asynchronous context.

        @param self Current instance.
        @param exc_type Exception type, if any.
        @param exc Exception instance, if any.
        @param tb Exception traceback, if any.
        """
        return None

    async def search_track(self, artist: str, title: str) -> list[Recording]:
        """! @brief Search configured search-capable providers, in order.

        @param self Current instance.
        @param artist Artist name.
        @param title Track title.
        @return Combined recording candidates in provider order.

        A list is returned because artist/title pairs can identify multiple recordings.
        This initial implementation propagates provider errors; retries and
        partial-failure handling will be introduced with actual adapters.
        """
        matches: list[Recording] = []
        for provider in self._providers:
            if isinstance(provider, MusicSearchIf):
                matches.extend(await provider.search_recordings(artist, title))
        return matches
