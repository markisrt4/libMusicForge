from datetime import datetime, timezone

from musicforge.airplay.storage import AirplayStore


def test_sqlite_observation_insert_is_idempotent(tmp_path):
    timestamp = datetime(2026, 10, 30, 6, 14, tzinfo=timezone.utc)
    with AirplayStore(tmp_path / "airplay.sqlite3") as store:
        assert store.add("WOMC", "Bon Jovi - Livin' On A Prayer", timestamp, 20)
        assert not store.add("WOMC", "Bon Jovi - Livin' On A Prayer", timestamp, 20)
        assert not store.add("WOMC", "invalid", timestamp, 21)
        rows = store.connection.execute(
            "SELECT station, artist, title FROM airplay_observations"
        ).fetchall()
        assert rows == [("WOMC", "Bon Jovi", "Livin' On A Prayer")]
