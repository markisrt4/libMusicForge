"""Collect ICY song changes without saving or decoding audio.

Examples:
  python examples/collect_radio_icy.py --station WNIC 'https://stream.revma.ihrhls.com/zc1153?streamid=1153' --station WRIF 'https://playerservices.streamtheworld.com/api/livestream-redirect/WRIFFMAACIHR.aac'

Each station runs in its own task and reconnects on stream failure.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

import httpx

from musicforge.airplay.icy import IcyMetadataDecoder, song_label
from musicforge.airplay.storage import AirplayStore


async def listen(station: str, url: str, queue: asyncio.Queue[tuple[str, str, datetime]],
                 reconnect_seconds: float) -> None:
    previous: str | None = None
    async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(20, read=None)) as client:
        while True:
            try:
                async with client.stream("GET", url, headers={"Icy-MetaData": "1",
                                                               "User-Agent": "libMusicForge/0.1"}) as response:
                    response.raise_for_status()
                    raw_interval = response.headers.get("icy-metaint")
                    if raw_interval is None:
                        raise ValueError("stream did not provide icy-metaint")
                    decoder = IcyMetadataDecoder(int(raw_interval))
                    async for chunk in response.aiter_raw():
                        for fields in decoder.feed(chunk):
                            label = song_label(fields)
                            if label is None:
                                continue
                            if label != previous:
                                previous = label
                                await queue.put((station, label, datetime.now(timezone.utc)))
            except (httpx.HTTPError, ValueError, OSError) as exc:
                print(f"{station}: stream error: {exc}; reconnecting", flush=True)
            await asyncio.sleep(reconnect_seconds)


async def write_events(queue: asyncio.Queue[tuple[str, str, datetime]],
                       database: str) -> None:
    counters: dict[str, int] = {}
    with AirplayStore(database) as store:
        while True:
            station, label, observed_at = await queue.get()
            counters[station] = counters.get(station, 0) + 1
            if store.add(station, label, observed_at, counters[station], source="icy"):
                print(f"{station}: {observed_at.isoformat()} {label}", flush=True)
            queue.task_done()


async def collect(stations: list[list[str]], database: str,
                  reconnect_seconds: float) -> None:
    queue: asyncio.Queue[tuple[str, str, datetime]] = asyncio.Queue()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(write_events(queue, database))
        for station, url in stations:
            tasks.create_task(listen(station, url, queue, reconnect_seconds))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", nargs=2, action="append", required=True,
                        metavar=("NAME", "URL"))
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--reconnect-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.reconnect_seconds <= 0:
        parser.error("--reconnect-seconds must be positive")
    if len({name for name, _ in args.station}) != len(args.station):
        parser.error("station names must be unique")
    try:
        asyncio.run(collect(args.station, args.database, args.reconnect_seconds))
    except KeyboardInterrupt:
        print("Collector stopped.")


if __name__ == "__main__":
    main()
