import asyncio

import httpx
import pytest

from musicforge.providers.lastfm import LastFmAdapter, LastFmError


def run(coro):
    return asyncio.run(coro)


def test_artist_metrics_are_attributed() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={
            "artist": {"name": "Collective Soul", "stats": {
                "listeners": "12345", "playcount": "67890"
            }}
        })

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with LastFmAdapter(api_key="test-key", client=client) as adapter:
                stats = await adapter.artist_statistics("Collective Soul")
        assert [(s.metric, s.value, s.unit) for s in stats] == [
            ("global_listener_count", 12345, "listeners"),
            ("global_scrobble_count", 67890, "scrobbles"),
        ]
        assert all(s.provider == "lastfm" for s in stats)
        assert all(s.subject.namespace == "lastfm:artist" for s in stats)

    run(scenario())
    assert seen[0].url.params["method"] == "artist.getinfo"
    assert seen[0].url.params["api_key"] == "test-key"


def test_track_metrics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "track": {
                "name": "Burn",
                "artist": {"name": "Collective Soul"},
                "listeners": "100",
                "playcount": "250",
            }
        })

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with LastFmAdapter(api_key="test-key", client=client) as adapter:
                stats = await adapter.track_statistics("Collective Soul", "Burn")
        assert stats[0].subject.value == "Collective Soul::Burn"
        assert stats[1].metric == "global_scrobble_count"
        assert stats[1].value == 250

    run(scenario())


def test_api_error_and_malformed_counts() -> None:
    async def scenario() -> None:
        for payload in (
            {"error": 10, "message": "Invalid API key"},
            {"artist": {"name": "A", "stats": {"listeners": "not-a-number"}}},
        ):
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=payload)
            )) as client:
                async with LastFmAdapter(api_key="test-key", client=client) as adapter:
                    with pytest.raises(LastFmError):
                        await adapter.artist_statistics("A")

    run(scenario())


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        LastFmAdapter(api_key="")

    async def scenario() -> None:
        async with LastFmAdapter(api_key="test-key") as adapter:
            with pytest.raises(ValueError):
                await adapter.track_statistics("", "Burn")

    run(scenario())
