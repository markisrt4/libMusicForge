"""Poll authorized HLS streams and store candidate song changes in SQLite.

Stops on Ctrl+C. Polls are sequential per cycle; each station has its own
continuity tracker. This is an observation collector, not certified airplay.
"""
from __future__ import annotations

import argparse
import asyncio
from time import monotonic
from urllib.parse import urljoin

import httpx

from musicforge.airplay import parse_media_playlist
from musicforge.airplay.diagnostics import HlsObservationTracker
from musicforge.airplay.storage import AirplayStore


async def fetch_playlist(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    if "#EXT-X-STREAM-INF:" not in response.text:
        return response.text
    lines = [line.strip() for line in response.text.splitlines() if line.strip()]
    variants = [line for line in lines if not line.startswith("#")]
    if not variants:
        raise ValueError("No HLS variants")
    media = await client.get(urljoin(str(response.url), variants[0]))
    media.raise_for_status()
    return media.text


async def collect(stations: list[list[str]], database: str, interval: float,
                  cycles: int | None) -> None:
    tracker = HlsObservationTracker()
    with AirplayStore(database) as store:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            cycle = 0
            while cycles is None or cycle < cycles:
                started = monotonic()
                for station, url in stations:
                    try:
                        playlist = parse_media_playlist(await fetch_playlist(client, url))
                        observations = tracker.observe(station, playlist)
                        for segment in observations:
                            if store.add(station, segment.title, segment.started_at,
                                         segment.sequence):
                                print(f"{station}: {segment.started_at} {segment.title}",
                                      flush=True)
                    except (httpx.HTTPError, ValueError) as exc:
                        print(f"{station}: error: {exc}", flush=True)
                cycle += 1
                if cycles is None or cycle < cycles:
                    await asyncio.sleep(max(0.0, interval - (monotonic() - started)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", nargs=2, action="append", required=True,
                        metavar=("NAME", "URL"))
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--cycles", type=int)
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")
    if args.cycles is not None and args.cycles < 1:
        parser.error("--cycles must be positive")
    try:
        asyncio.run(collect(args.station, args.database, args.interval, args.cycles))
    except KeyboardInterrupt:
        print("Collector stopped.")


if __name__ == "__main__":
    main()
