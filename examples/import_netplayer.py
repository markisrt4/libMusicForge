"""One-shot Netplayer playlist import. Run manually after checking site terms.

Example:
  python examples/import_netplayer.py --database airplay.sqlite3
This script makes exactly one request and never schedules polling.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

import httpx

from musicforge.airplay.netplayer import parse_netplayer
from musicforge.airplay.storage import AirplayStore

STATIONS = {
    "WRIF": "https://netplayer.net/radio/101-wrif-64370/recently-played",
    "WNIC": "https://netplayer.net/radio/100-3-wnic-34832/recently-played",
    "WOMC": "https://netplayer.net/radio/104-3-womc-detroit-95098/recently-played",
    "WYCD": "https://netplayer.net/radio/99-5-wycd-57061/recently-played",
    "WCSX": "https://netplayer.net/radio/94-7-wcsx-15859/recently-played",
    "WDVD": "https://netplayer.net/radio/96-3-wdvd-42425/recently-played",
    "WJLB": "https://netplayer.net/radio/97-9-wjlb-10376/recently-played",
    "ALT987": "https://netplayer.net/radio/alt-98-7-detroit-35557/recently-played",
    "BOUNCE1051": "https://netplayer.net/radio/105-1-the-bounce-63950/recently-played",
    "KISS1059": "https://netplayer.net/radio/105-9-kiss-fm-97425/recently-played",
}


async def import_station(station: str, url: str, database: str) -> None:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(url, headers={
            "User-Agent": "libMusicForge-manual-airplay-import/0.1",
            "Accept": "text/html",
        })
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "").lower():
            raise ValueError("Expected HTML playlist")
    plays = parse_netplayer(response.text)
    inserted = 0
    with AirplayStore(database) as store:
        for play in plays:
            # Timestamp identifies an occurrence; stable sequence makes repeated
            # imports idempotent while allowing repeated songs at different times.
            sequence = int(play.played_at.timestamp() * 1000)
            if store.add(station, play.label, play.played_at, sequence,
                         source="netplayer"):
                inserted += 1
    latest = max((p.played_at for p in plays), default=None)
    lag = ((datetime.now(timezone.utc) - latest).total_seconds() / 60
           if latest is not None else None)
    print(f"{station}: parsed={len(plays)} inserted={inserted} "
          f"latest={latest.isoformat() if latest else 'none'} "
          f"lag_minutes={round(lag, 1) if lag is not None else 'unknown'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", choices=sorted(STATIONS) + ["all"], default="WRIF")
    parser.add_argument("--database", default="airplay.sqlite3")
    args = parser.parse_args()
    async def run() -> None:
        for station in (sorted(STATIONS) if args.station == "all" else [args.station]):
            try:
                await import_station(station, STATIONS[station], args.database)
            except (httpx.HTTPError, ValueError) as exc:
                print(f"{station}: import failed: {type(exc).__name__}: {exc}", flush=True)
    asyncio.run(run())


if __name__ == "__main__":
    main()
