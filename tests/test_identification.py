import asyncio
from datetime import datetime, timezone

import pytest

from musicforge.identification import identify_and_enrich
from musicforge.models import Artist, Identifier, Recording, Statistic


class Metadata:
    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        return [
            Recording(title=title, artists=(Artist(artist),), identifiers=(Identifier("musicbrainz:recording", "id-1"),)),
            Recording(title=title, artists=(Artist(artist),), identifiers=(Identifier("musicbrainz:recording", "id-2"),)),
        ]


class Statistics:
    async def track_statistics(self, artist: str, title: str) -> list[Statistic]:
        return [
            Statistic(
                provider="lastfm", metric="global_scrobble_count", value=7002,
                observed_at=datetime.now(timezone.utc), unit="scrobbles",
                subject=Identifier("lastfm:track", f"{artist}::{title}"),
            )
        ]


def test_retains_candidates_without_false_identity() -> None:
    result = asyncio.run(identify_and_enrich(Metadata(), Statistics(), "Collective Soul", "Burn"))
    assert len(result.candidates) == 2
    assert result.statistics[0].value == 7002
    assert result.verified_recording_match is False
    assert result.match_method == "artist_title_lookup"
    assert result.statistics[0].subject.namespace == "lastfm:track"


def test_rejects_blank_search() -> None:
    with pytest.raises(ValueError):
        asyncio.run(identify_and_enrich(Metadata(), Statistics(), "", "Burn"))
