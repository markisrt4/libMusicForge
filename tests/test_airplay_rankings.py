"""Ranking tests: Detroit-local day boundaries and station filtering."""
from datetime import date

from musicforge.airplay.storage import AirplayStore
from examples.rank_airplay import rankings


def test_rankings_and_station_filter(tmp_path):
    path = tmp_path / "airplay.sqlite3"
    from datetime import datetime
    with AirplayStore(path) as store:
        samples = [
            ("WRIF", "Artist A - Song One", "2026-10-30T14:00:00+00:00"),
            ("WRIF", "Artist A - Song One", "2026-10-30T15:00:00+00:00"),
            ("WNIC", "Artist A - Song One", "2026-10-30T16:00:00+00:00"),
            ("WNIC", "Artist B - Song Two", "2026-10-30T17:00:00+00:00"),
            ("WRIF", "Artist C - Yesterday", "2026-10-30T03:00:00+00:00"),
        ]
        for i, (station, label, timestamp) in enumerate(samples):
            assert store.add(station, label, datetime.fromisoformat(timestamp), i, source="test")
    songs, artists = rankings(str(path), date(2026, 10, 30))
    assert songs[0] == ("Artist A", "Song One", 3, 2)
    assert len(songs) == 2
    assert artists[0] == ("Artist A", 3, 1)
    wrif_songs, _ = rankings(str(path), date(2026, 10, 30), station="WRIF")
    assert wrif_songs == [("Artist A", "Song One", 2, 1)]
    two_days, _ = rankings(str(path), date(2026, 10, 30), days=2)
    assert len(two_days) == 3
