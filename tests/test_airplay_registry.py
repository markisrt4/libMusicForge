import pytest

from musicforge.airplay.health import SourceStatus
from musicforge.airplay.registry import (
    DETROIT_STATIONS, RadioSource, RadioStation, SourceKind, choose_source,
)


def source(name, priority=100, verified=True):
    return RadioSource(name, SourceKind.ICY, "https://example.org/radio",
                       priority=priority, verified=verified)


def test_only_verified_sources_are_eligible():
    station = RadioStation("WRIF", (source("unverified", verified=False),))
    assert choose_source(station).source is None


def test_priority_is_respected_when_status_unknown():
    station = RadioStation("TEST", (source("backup", 20), source("primary", 10)))
    assert choose_source(station).source.name == "primary"


def test_unhealthy_primary_uses_verified_fallback():
    station = RadioStation("TEST", (source("primary", 10), source("backup", 20)))
    selected = choose_source(station, {"primary": SourceStatus.EMPTY_METADATA})
    assert selected.source.name == "backup"


def test_healthy_backup_beats_unknown_primary():
    station = RadioStation("TEST", (source("primary", 10), source("backup", 20)))
    selected = choose_source(station, {"backup": SourceStatus.HEALTHY})
    assert selected.source.name == "backup"


def test_no_songs_is_not_assumed_broken():
    station = RadioStation("TEST", (source("primary"),))
    assert choose_source(station, {"primary": SourceStatus.NO_SONGS}).source


def test_no_fallback_if_every_source_is_unhealthy():
    station = RadioStation("TEST", (source("primary"),))
    assert choose_source(station, {"primary": SourceStatus.STALE}).source is None


def test_registry_marks_wrif_unverified():
    wrif = next(station for station in DETROIT_STATIONS
                if station.callsign == "WRIF")
    assert choose_source(wrif).source is None


def test_rejects_invalid_registry_entries():
    with pytest.raises(ValueError):
        source("x", -1)
    with pytest.raises(ValueError):
        RadioSource("bad", SourceKind.ICY, "file:///tmp/music")
    with pytest.raises(ValueError):
        RadioStation("TEST", (source("same"), source("same")))
