"""Best-effort, staggered Netplayer airplay collector.

Each cycle requests each configured station once, in sequence. Use --once to
test without leaving a long-running process. Only run automated polling where
the site's access rules permit it.

Example:
  python examples/collect_radio_netplayer.py --database airplay.sqlite3 --once
  python examples/collect_radio_netplayer.py --database airplay.sqlite3
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from time import monotonic

import httpx

from import_netplayer import STATIONS, import_station


def station_names(selection: str) -> list[str]:
    """Return a stable list of known stations."""
    if selection == "all":
        return sorted(STATIONS)
    if selection not in STATIONS:
        raise ValueError(f"Unknown station: {selection}")
    return [selection]


async def collect_cycle(
    names: list[str], database: str, stagger_seconds: float,
) -> tuple[int, int]:
    """Collect each station once; continue when a single fetch fails."""
    successes = 0
    failures = 0
    for index, station in enumerate(names):
        if index:
            await asyncio.sleep(stagger_seconds)
        try:
            await import_station(station, STATIONS[station], database)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            failures += 1
            print(f"{station}: failed ({type(exc).__name__}: {exc})", flush=True)
        else:
            successes += 1
    return successes, failures


async def run(
    names: list[str], database: str, interval_seconds: float,
    stagger_seconds: float, once: bool = False,
) -> None:
    if interval_seconds <= 0 or stagger_seconds < 0:
        raise ValueError("interval must be positive; stagger must be nonnegative")
    cycle = 0
    while True:
        cycle += 1
        started = monotonic()
        print(f"Netplayer cycle {cycle} started "
              f"{datetime.now(timezone.utc).isoformat()} "
              f"stations={','.join(names)}", flush=True)
        successes, failures = await collect_cycle(names, database, stagger_seconds)
        print(f"Netplayer cycle {cycle} complete: "
              f"success={successes} failed={failures}", flush=True)
        if once:
            return
        elapsed = monotonic() - started
        await asyncio.sleep(max(0.0, interval_seconds - elapsed))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--station", choices=["all", *sorted(STATIONS)], default="all")
    parser.add_argument("--interval-hours", type=float, default=2.0,
                        help="Hours between the start of each collection cycle (default: 2)")
    parser.add_argument("--stagger-seconds", type=float, default=10.0,
                        help="Delay between station requests (default: 10)")
    parser.add_argument("--once", action="store_true",
                        help="Collect one cycle, then exit")
    args = parser.parse_args()
    if args.interval_hours <= 0 or args.stagger_seconds < 0:
        parser.error("--interval-hours must be positive; --stagger-seconds nonnegative")
    try:
        asyncio.run(run(station_names(args.station), args.database,
                        args.interval_hours * 3600, args.stagger_seconds,
                        once=args.once))
    except KeyboardInterrupt:
        print("Netplayer collector stopped.", flush=True)


if __name__ == "__main__":
    main()
