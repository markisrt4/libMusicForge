import asyncio

from musicforge import Artist, Identifier, MusicForge, Recording
from musicforge.interfaces import MusicSearchIf


class FakeSearch:
    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        return [Recording(title=title, artists=(Artist(name=artist),))]


def test_search_provider_and_async_context() -> None:
    async def run() -> None:
        async with MusicForge(providers=[FakeSearch()]) as forge:
            tracks = await forge.search_track("Collective Soul", "Burn")
        assert len(tracks) == 1
        assert tracks[0].title == "Burn"
        assert tracks[0].artists[0].name == "Collective Soul"

    asyncio.run(run())


def test_no_provider_returns_empty_results() -> None:
    assert asyncio.run(MusicForge().search_track("Unknown", "Unknown")) == []


def test_provider_protocol_is_structural() -> None:
    assert isinstance(FakeSearch(), MusicSearchIf)


def test_identifier_keeps_namespace() -> None:
    assert Identifier("musicbrainz:recording", "abc") != Identifier("spotify:track", "abc")
