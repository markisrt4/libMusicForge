"""Reusable read-only queries for observed radio airplay."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DETROIT = ZoneInfo("America/Detroit")


def date_bounds(day: date, days: int) -> tuple[str, str]:
    if days < 1:
        raise ValueError("days must be positive")
    start = datetime.combine(day - timedelta(days=days - 1), time.min, tzinfo=DETROIT)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=DETROIT)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def chart(database: str | Path, *, kind: str, day: date, days: int = 1,
          station: str | None = None, limit: int = 20) -> list[dict]:
    if kind not in ("songs", "artists"):
        raise ValueError("invalid chart kind")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    start, end = date_bounds(day, days)
    where = "observed_at >= ? AND observed_at < ?"
    params: list[object] = [start, end]
    if station:
        where += " AND station = ?"
        params.append(station)
    if kind == "songs":
        sql = f"""SELECT artist, title, COUNT(*) AS plays, COUNT(DISTINCT station) AS stations
                  FROM airplay_observations WHERE {where}
                  GROUP BY artist, title
                  ORDER BY plays DESC, artist COLLATE NOCASE, title COLLATE NOCASE LIMIT ?"""
    else:
        sql = f"""SELECT artist, COUNT(*) AS plays, COUNT(DISTINCT title) AS songs
                  FROM airplay_observations WHERE {where}
                  GROUP BY artist ORDER BY plays DESC, artist COLLATE NOCASE LIMIT ?"""
    with sqlite3.connect(f"file:{Path(database).resolve()}?mode=ro", uri=True) as conn:
        rows = conn.execute(sql, (*params, limit)).fetchall()
    keys = ("artist", "title", "plays", "stations") if kind == "songs" else ("artist", "plays", "songs")
    return [{"rank": i, **dict(zip(keys, row))} for i, row in enumerate(rows, 1)]


def stations(database: str | Path) -> list[dict]:
    with sqlite3.connect(f"file:{Path(database).resolve()}?mode=ro", uri=True) as conn:
        rows = conn.execute("""SELECT station, COUNT(*), MAX(observed_at)
                               FROM airplay_observations GROUP BY station ORDER BY station""").fetchall()
    return [{"station": name, "observations": count, "latest_observed_at": latest}
            for name, count, latest in rows]
