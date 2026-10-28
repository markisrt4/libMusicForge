import asyncio
import json

import httpx
import pytest

from musicforge import Identifier, MusicForge
from musicforge.providers.musicbrainz import MusicBrainzAdapter, MusicBrainzError

RID = "f1c89f52-9381-49a6-a5f4-17b02a2b819b"
ALBUM = "930dfd3c-abc9-4f4e-b54d-145b88b6e80e"
RECORDING = {
    "id": RID,
    "title": "Burn",
    "length": 234000,
    "artist-credit": [{"artist": {"id": "9f4a21b2-bdc1-4a3b-b35a-45f0a4a6b98e", "name": "Collective Soul"}}],
}


def run(coro):
    return asyncio.run(coro)


def test_search_and_normalization() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"recordings": [RECORDING]})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with MusicBrainzAdapter(contact="dev@example.org", client=client, min_interval=0) as provider:
                results = await MusicForge([provider]).search_track("Collective Soul", "Burn")
        assert len(results) == 1
        assert results[0].artists[0].name == "Collective Soul"
        assert results[0].duration_ms == 234000
        assert results[0].identifiers == (Identifier("musicbrainz:recording", RID),)

    run(scenario())
    assert "libMusicForge" in requests[0].headers["User-Agent"]
    assert requests[0].url.params["fmt"] == "json"
    assert 'recording:"Burn"' in requests[0].url.params["query"]


def test_recording_and_release_lookup() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/release/" in request.url.path:
            return httpx.Response(200, json={
                "title": "Home",
                "artist-credit": RECORDING["artist-credit"],
                "media": [{"tracks": [{"recording": RECORDING}]}],
            })
        return httpx.Response(200, json=RECORDING)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with MusicBrainzAdapter(contact="dev@example.org", client=client, min_interval=0) as adapter:
                recording = await adapter.get_recording(Identifier("musicbrainz:recording", RID))
                release = await adapter.get_release(Identifier("musicbrainz:release", ALBUM))
                assert recording is not None and recording.title == "Burn"
                assert release is not None and release.title == "Home"
                assert release.recordings[0].title == "Burn"

    run(scenario())


def test_404_returns_none_and_500_raises() -> None:
    async def scenario() -> None:
        for status in (404, 500):
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(status)
            )) as client:
                adapter = MusicBrainzAdapter(contact="dev@example.org", client=client, min_interval=0)
                if status == 404:
                    assert await adapter.get_recording(Identifier("musicbrainz:recording", RID)) is None
                else:
                    with pytest.raises(MusicBrainzError):
                        await adapter.get_recording(Identifier("musicbrainz:recording", RID))

    run(scenario())


def test_reject_invalid_identifier_and_empty_query() -> None:
    async def scenario() -> None:
        async with MusicBrainzAdapter(contact="dev@example.org") as adapter:
            with pytest.raises(ValueError):
                await adapter.get_recording(Identifier("spotify:track", RID))
            with pytest.raises(ValueError):
                await adapter.get_release(Identifier("musicbrainz:release", "../bad"))
            with pytest.raises(ValueError):
                await adapter.search_recordings("", "Burn")

    run(scenario())
