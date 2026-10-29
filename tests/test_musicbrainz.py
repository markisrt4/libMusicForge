import asyncio

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


def test_transient_503_retries_then_succeeds() -> None:
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        if len(attempts) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"recordings": [RECORDING]})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with MusicBrainzAdapter(
                contact="dev@example.org", client=client, min_interval=0, max_retries=2
            ) as adapter:
                results = await adapter.search_recordings("Collective Soul", "Burn")
                assert results[0].title == "Burn"

    run(scenario())
    assert len(attempts) == 3


def test_503_exhaustion_raises() -> None:
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request)
        return httpx.Response(503)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with MusicBrainzAdapter(
                contact="dev@example.org", client=client, min_interval=0, max_retries=0
            ) as adapter:
                with pytest.raises(MusicBrainzError, match="503"):
                    await adapter.search_recordings("Collective Soul", "Burn")

    run(scenario())
    assert len(attempts) == 1


def test_recording_details_include_release_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["inc"] == "artist-credits+releases"
        return httpx.Response(200, json={
            **RECORDING,
            "releases": [
                {"id": ALBUM, "title": "Home", "date": "1995-03-14"},
                {"id": "aa70d53e-2904-452e-bef5-b2780c5c21cb", "title": "Greatest Hits"},
            ],
        })

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with MusicBrainzAdapter(
                contact="dev@example.org", client=client, min_interval=0
            ) as adapter:
                details = await adapter.get_recording_details(
                    Identifier("musicbrainz:recording", RID)
                )
                assert details is not None
                assert details.recording.duration_ms == 234000
                assert details.recording.artists[0].name == "Collective Soul"
                assert details.releases[0].title == "Home"
                assert details.releases[0].date == "1995-03-14"
                assert details.releases[1].date is None

    run(scenario())


def test_recording_details_not_found() -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(404)
        )) as client:
            async with MusicBrainzAdapter(
                contact="dev@example.org", client=client, min_interval=0
            ) as adapter:
                assert await adapter.get_recording_details(
                    Identifier("musicbrainz:recording", RID)
                ) is None

    run(scenario())
