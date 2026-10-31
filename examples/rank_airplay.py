"""Rank observed radio airplay for a Detroit-local day or date range.

Examples:
  python examples/rank_airplay.py --day 2026-10-30 --limit 15
  python examples/rank_airplay.py --day 2026-10-30 --days 7 --station WRIF
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DETROIT = ZoneInfo("America/Detroit")


def bounds(day: date, days: int) -> tuple[str, str]:
    if days < 1:
        raise ValueError("days must be >= 1")
    start = datetime.combine(day - timedelta(days=days - 1), time.min, tzinfo=DETROIT)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=DETROIT)
    return (start.astimezone(timezone.utc).isoformat(),
            end.astimezone(timezone.utc).isoformat())


def rankings(database: str, day: date, days: int = 1,
             station: str | None = None, limit: int = 20):
    if limit < 1:
        raise ValueError("limit must be >= 1")
    start, end = bounds(day, days)
    station_clause = " AND station = ?" if station else ""
    params = [start, end]
    if station:
        params.append(station)
    with sqlite3.connect(database) as conn:
        songs = conn.execute(
            """SELECT artist, title, COUNT(*) AS plays,
                      COUNT(DISTINCT station) AS stations
               FROM airplay_observations
               WHERE observed_at >= ? AND observed_at < ?""" + station_clause +
            """ GROUP BY artist, title
                ORDER BY plays DESC, artist COLLATE NOCASE, title COLLATE NOCASE
                LIMIT ?""",
            (*params, limit),
        ).fetchall()
        artists = conn.execute(
            """SELECT artist, COUNT(*) AS plays,
                      COUNT(DISTINCT title) AS songs
               FROM airplay_observations
               WHERE observed_at >= ? AND observed_at < ?""" + station_clause +
            """ GROUP BY artist
                ORDER BY plays DESC, artist COLLATE NOCASE
                LIMIT ?""",
            (*params, limit),
        ).fetchall()
    return songs, artists


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(DETROIT).date(),
                        help="Last Detroit-local date included, YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=1,
                        help="Number of Detroit-local calendar days ending on --day")
    parser.add_argument("--station", help="Optional callsign, e.g. WRIF")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.days < 1 or args.limit < 1:
        parser.error("--days and --limit must be positive")
    songs, artists = rankings(args.database, args.day, args.days,
                              args.station, args.limit)
    print(f"Observed airplay rankings: {args.days} Detroit day(s) through "
          f"{args.day}" + (f" [{args.station}]" if args.station else " [all stations]"))
    print("\nSONGS (plays, stations)")
    for index, (artist, title, plays, stations) in enumerate(songs, 1):
        print(f"{index:>2}. {artist} - {title}: {plays} plays / {stations} stations")
    print("\nARTISTS (plays, distinct songs)")
    for index, (artist, plays, titles) in enumerate(artists, 1):
        print(f"{index:>2}. {artist}: {plays} plays / {titles} songs")


if __name__ == "__main__":
    main()
