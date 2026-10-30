"""Report recorded airplay and observation coverage for a Detroit calendar day.

Counts reflect observations in SQLite, not guaranteed complete broadcast logs.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DETROIT = ZoneInfo("America/Detroit")


def day_bounds(day: date) -> tuple[str, str]:
    start = datetime.combine(day, time.min, tzinfo=DETROIT)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=DETROIT)
    return (start.astimezone(timezone.utc).isoformat(),
            end.astimezone(timezone.utc).isoformat())


def daily_counts(database: str, day: date) -> list[tuple[str, int, int, str, str]]:
    start, end = day_bounds(day)
    with sqlite3.connect(database) as conn:
        return conn.execute(
            """SELECT station, COUNT(*),
                      COUNT(DISTINCT artist || char(0) || title),
                      MIN(observed_at), MAX(observed_at)
               FROM airplay_observations
               WHERE observed_at >= ? AND observed_at < ?
               GROUP BY station ORDER BY station""",
            (start, end),
        ).fetchall()


def local_clock(utc_timestamp: str) -> str:
    return datetime.fromisoformat(utc_timestamp).astimezone(DETROIT).strftime("%H:%M")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(DETROIT).date())
    args = parser.parse_args()
    print(f"Detroit airplay date: {args.day} (observed data only)")
    for station, plays, songs, earliest, latest in daily_counts(args.database, args.day):
        span = (datetime.fromisoformat(latest) -
                datetime.fromisoformat(earliest)).total_seconds() / 3600
        print(f"{station}: plays={plays} unique_songs={songs} "
              f"first_local={local_clock(earliest)} "
              f"last_local={local_clock(latest)} "
              f"observation_span_hours={span:.1f} "
              "(not a completeness guarantee)")


if __name__ == "__main__":
    main()
