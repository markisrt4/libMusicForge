import asyncio

import pytest

from musicforge.models import Artist, Recording
from musicforge.playback import MusicBrainzNameResolver, TrackIdentity


class Search:
    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        assert (artist, title) == ("Collective Soul", "Burn")
        return [
            Recording(title="Burn", artists=(Artist("Collective Soul"),), duration_ms=215000),
            Recording(title="Burn", artists=(Artist("Collective Soul"),), duration_ms=245000),
        ]


def test_resolve_preserves_ambiguity_and_evidence() -> None:
    track = TrackIdentity(
        source="mpris", artist="Collective Soul", title="Burn",
        duration_ms=216000, isrc="USXXX0000001",
    )
    result = asyncio.run(MusicBrainzNameResolver(Search()).resolve(track))
    assert result.verified is False
    assert len(result.candidates) == 2
    assert result.candidates[0].duration_difference_ms == 1000
    assert result.candidates[0].evidence == (
        "exact_title", "exact_artist_credit", "duration_within_2s",
    )
    assert result.candidates[1].duration_difference_ms == 29000
    assert "duration_within_2s" not in result.candidates[1].evidence
    assert result.observed.isrc == "USXXX0000001"


def test_identity_validation() -> None:
    with pytest.raises(ValueError):
        TrackIdentity(source="mpd", artist="", title="Burn")
    with pytest.raises(ValueError):
        TrackIdentity(source="mpd", artist="Collective Soul", title="Burn", duration_ms=-1)


def test_missing_duration_does_not_invent_match() -> None:
    track = TrackIdentity(source="android", artist="Collective Soul", title="Burn")
    result = asyncio.run(MusicBrainzNameResolver(Search()).resolve(track))
    assert result.candidates[0].duration_difference_ms is None
    assert "duration_within_2s" not in result.candidates[0].evidence
