"""Minimal orchestration entry point for music provider capabilities."""

from collections.abc import Iterable

from musicforge.interfaces import MusicSearchIf
from musicforge.models import Recording


class MusicForge:
    """Library entry point. Providers are optional and independently configured."""

    def __init__(self, providers: Iterable[object] = ()) -> None:
        self._providers = tuple(providers)

    async def __aenter__(self) -> "MusicForge":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def search_track(self, artist: str, title: str) -> list[Recording]:
        """Search configured search-capable providers, in order.

        A list is returned because artist/title pairs can identify multiple recordings.
        This initial implementation propagates provider errors; retries and
        partial-failure handling will be introduced with actual adapters.
        """
        matches: list[Recording] = []
        for provider in self._providers:
            if isinstance(provider, MusicSearchIf):
                matches.extend(await provider.search_recordings(artist, title))
        return matches
