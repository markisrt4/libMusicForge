"""Identify unusually long intervals between observed airplay records.

Gaps are signals for investigation, not proof that broadcasts were missed.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DETROIT = ZoneInfo("America/Detroit")


def find_gaps(database: str, day: date, threshold_minutes: float = 30.0):
    if threshold_minutes <= 0:
        raise ValueError("threshold_minutes must be positive")
    start = datetime.combine(day, datetime.min.time(), tzinfo=DETROIT)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=DETROIT)
    with sqlite3.connect(database) as conn:
        rows = conn.execute(
            """SELECT DISTINCT station, observed_at
               FROM airplay_observations
               WHERE observed_at >= ? AND observed_at < ?
               ORDER BY station, observed_at""",
            (start.astimezone(timezone.utc).isoformat(),
             end.astimezone(timezone.utc).isoformat()),
        ).fetchall()
    previous = {}
    gaps = []
    for station, stamp in rows:
        current = datetime.fromisoformat(stamp)
        earlier = previous.get(station)
        if earlier is not None:
            minutes = (current - earlier).total_seconds() / 60
            if minutes >= threshold_minutes:
                gaps.append((station, earlier, current, minutes))
        previous[station] = current
    return gaps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(DETROIT).date())
    parser.add_argument("--threshold-minutes", type=float, default=30.0)
    args = parser.parse_args()
    if args.threshold_minutes <= 0:
        parser.error("--threshold-minutes must be positive")
    gaps = find_gaps(args.database, args.day, args.threshold_minutes)
    print(f"Detroit date: {args.day}; observation gaps >= {args.threshold_minutes:g} minutes")
    if not gaps:
        print("No qualifying gaps between recorded plays (day boundaries not checked).")
    for station, start, end, minutes in gaps:
        fmt = lambda value: value.astimezone(DETROIT).strftime("%H:%M:%S")
        print(f"{station}: {fmt(start)} to {fmt(end)} ({minutes:.1f} minutes)")


if __name__ == "__main__":
    main()
