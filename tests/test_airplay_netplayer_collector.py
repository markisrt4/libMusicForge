"""Best-effort Netplayer collection orchestration tests."""
import asyncio

import pytest

from examples import collect_radio_netplayer as collector


def test_station_selection():
    assert collector.station_names("all") == sorted(collector.STATIONS)
    assert collector.station_names("WRIF") == ["WRIF"]
    with pytest.raises(ValueError):
        collector.station_names("UNKNOWN")


def test_cycle_continues_after_station_failure(monkeypatch):
    called = []
    async def fake_import(station, url, database):
        called.append(station)
        if station == "WNIC":
            raise ValueError("bad playlist")
    async def no_sleep(_seconds):
        return None
    monkeypatch.setattr(collector, "import_station", fake_import)
    monkeypatch.setattr(collector.asyncio, "sleep", no_sleep)
    result = asyncio.run(collector.collect_cycle(["WNIC", "WRIF"], "test.sqlite3", 0))
    assert result == (1, 1)
    assert called == ["WNIC", "WRIF"]


def test_once_runs_exactly_one_cycle(monkeypatch):
    calls = []
    async def fake_cycle(names, database, stagger_seconds):
        calls.append(tuple(names))
        return (1, 0)
    monkeypatch.setattr(collector, "collect_cycle", fake_cycle)
    asyncio.run(collector.run(["WRIF"], "test.sqlite3", 7200, 0, once=True))
    assert calls == [("WRIF",)]
