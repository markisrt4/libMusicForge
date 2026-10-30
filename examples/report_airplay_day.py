"""Print airplay counts for a Detroit local calendar day.

Example: python examples/report_airplay_day.py --database airplay.sqlite3
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def day_bounds(day: date) -> tuple[str, str]:
    zone = ZoneInfo("America/Detroit")
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def daily_counts(database: str, day: date) -> list[tuple[str, int, int, str]]:
    start, end = day_bounds(day)
    with sqlite3.connect(database) as conn:
        return conn.execute(
            """SELECT station, COUNT(*),
                      COUNT(DISTINCT artist || char(0) || title),
                      MAX(observed_at)
               FROM airplay_observations
               WHERE observed_at >= ? AND observed_at < ?
               GROUP BY station ORDER BY station""",
            (start, end),
        ).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo("America/Detroit")).date())
    args = parser.parse_args()
    print(f"Detroit airplay date: {args.day}")
    for station, plays, songs, latest in daily_counts(args.database, args.day):
        print(f"{station}: plays={plays} unique_songs={songs} latest_utc={latest}")


if __name__ == "__main__":
    main()
