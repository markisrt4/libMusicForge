import asyncio
from datetime import datetime, timezone

import pytest

from musicforge.analytics import compare_tracks
from musicforge.models import Identifier, Statistic


def metric(name: str, value: int, provider: str = "lastfm") -> Statistic:
    return Statistic(
        provider=provider,
        metric=name,
        value=value,
        observed_at=datetime.now(timezone.utc),
        unit="listeners" if name == "global_listener_count" else "scrobbles",
        subject=Identifier("lastfm:track", "test"),
    )


class FakeProvider:
    async def track_statistics(self, artist: str, title: str) -> list[Statistic]:
        if title == "Burn":
            return [metric("global_listener_count", 1559), metric("global_scrobble_count", 7002)]
        if title == "Unknown":
            return []
        return [metric("global_listener_count", 100), metric("global_scrobble_count", 1000)]


def test_compare_sort_and_ratio() -> None:
    async def scenario() -> None:
        rows = await compare_tracks(
            FakeProvider(),
            [("Collective Soul", "Burn"), ("Band", "Other")],
            sort_by="ratio",
        )
        assert rows[0].title == "Other"
        assert rows[0].scrobbles_per_listener == 10
        assert rows[1].scrobbles_per_listener == pytest.approx(7002 / 1559)
        by_listeners = await compare_tracks(
            FakeProvider(),
            [("Band", "Other"), ("Collective Soul", "Burn")],
        )
        assert by_listeners[0].title == "Burn"

    asyncio.run(scenario())


def test_missing_counts_and_invalid_sort() -> None:
    async def scenario() -> None:
        rows = await compare_tracks(
            FakeProvider(), [("Band", "Unknown"), ("Band", "Other")],
            sort_by="ratio",
        )
        assert rows[-1].scrobbles_per_listener is None
        assert rows[-1].listeners is None
        with pytest.raises(ValueError):
            await compare_tracks(FakeProvider(), [("Band", "Other")], sort_by="invalid")
        with pytest.raises(ValueError):
            await compare_tracks(FakeProvider(), [("", "Other")])

    asyncio.run(scenario())


def test_provider_provenance() -> None:
    class WrongProvider:
        async def track_statistics(self, artist: str, title: str) -> list[Statistic]:
            return [metric("global_listener_count", 9000, "another-provider")]

    async def scenario() -> None:
        rows = await compare_tracks(WrongProvider(), [("Band", "Track")])
        assert rows[0].listeners is None

    asyncio.run(scenario())
