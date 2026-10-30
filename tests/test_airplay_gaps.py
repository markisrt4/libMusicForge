"""Gap detection should distinguish timestamps and ignore duplicate observations."""
import sqlite3
from datetime import date

import pytest

from examples.report_airplay_gaps import find_gaps


def test_detects_gaps_and_deduplicates_timestamps(tmp_path):
    path = tmp_path / "plays.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE airplay_observations (station TEXT, observed_at TEXT)")
        db.executemany("INSERT INTO airplay_observations VALUES (?, ?)", [
            ("WRIF", "2026-10-30T14:00:00+00:00"),
            ("WRIF", "2026-10-30T14:00:00+00:00"),
            ("WRIF", "2026-10-30T14:15:00+00:00"),
            ("WRIF", "2026-10-30T15:00:00+00:00"),
            ("WNIC", "2026-10-30T14:00:00+00:00"),
        ])
    gaps = find_gaps(str(path), date(2026, 10, 30), 30)
    assert len(gaps) == 1
    assert gaps[0][0] == "WRIF"
    assert gaps[0][3] == 45


def test_invalid_threshold(tmp_path):
    with pytest.raises(ValueError):
        find_gaps(str(tmp_path / "unused.sqlite3"), date(2026, 10, 30), 0)
