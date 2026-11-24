"""Exercise cross-provider lookup through the real HTTP adapters."""

import asyncio

import httpx
import pytest

from musicforge.identification import identify_and_enrich
from musicforge.models import Identifier
from musicforge.providers.lastfm import LastFmAdapter
from musicforge.providers.musicbrainz import MusicBrainzAdapter


@pytest.mark.parametrize("lastfm_status", [200, 503])
def test_lookup_keeps_recording_identity_and_track_totals_separate(
    lastfm_status: int,
) -> None:
    recording_id = "f1c89f52-9381-49a6-a5f4-17b02a2b819b"

    def musicbrainz_response(request: httpx.Request) -> httpx.Response:
        assert 'recording:"Burn"' in request.url.params["query"]
        return httpx.Response(
            200,
            json={
                "recordings": [
                    {
                        "id": recording_id,
                        "title": "Burn",
                        "artist-credit": [{"artist": {"name": "Collective Soul"}}],
                    }
                ],
            },
        )

    def lastfm_response(request: httpx.Request) -> httpx.Response:
        assert request.url.params["method"] == "track.getInfo"
        assert request.url.params["track"] == "Burn"
        return httpx.Response(
            lastfm_status,
            json={
                "track": {"listeners": "100", "playcount": "250"},
            },
        )

    async def scenario() -> None:
        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(musicbrainz_response)
            ) as mb_client,
            httpx.AsyncClient(
                transport=httpx.MockTransport(lastfm_response)
            ) as lf_client,
            MusicBrainzAdapter(
                contact="dev@example.org", client=mb_client, min_interval=0
            ) as mb,
            LastFmAdapter(api_key="test-key", client=lf_client) as lf,
        ):
            result = await identify_and_enrich(mb, lf, "Collective Soul", "Burn")

        assert result.metadata_error is None
        assert len(result.candidates) == 1
        assert result.candidates[0].identifiers == (
            Identifier("musicbrainz:recording", recording_id),
        )
        assert result.verified_recording_match is False
        if lastfm_status == 200:
            assert result.statistics_error is None
            assert [(stat.value, stat.unit) for stat in result.statistics] == [
                (100, "listeners"),
                (250, "scrobbles"),
            ]
            assert all(
                stat.subject.namespace == "lastfm:track" for stat in result.statistics
            )
        else:
            assert result.statistics == ()
            assert result.statistics_error is not None

    asyncio.run(scenario())
