"""Collect ICY radio song changes and report stream health (audio discarded)."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from time import monotonic

import httpx

from musicforge.airplay.icy import IcyMetadataDecoder, song_label
from musicforge.airplay.health import classify_icy_health
from musicforge.airplay.storage import AirplayStore


async def listen(station: str, url: str, queue: asyncio.Queue[tuple[str, str, datetime]],
                 reconnect_seconds: float, diagnostics_interval: float) -> None:
    previous: str | None = None
    bytes_seen = changes = ignored = repeats = blocks = empty = parsed = 0
    next_report = monotonic() + diagnostics_interval
    connected_since: float | None = None
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=httpx.Timeout(20, read=None)
    ) as client:
        while True:
            decoder: IcyMetadataDecoder | None = None
            try:
                async with client.stream(
                    "GET", url, headers={"Icy-MetaData": "1",
                                         "User-Agent": "libMusicForge/0.1"}
                ) as response:
                    response.raise_for_status()
                    raw_interval = response.headers.get("icy-metaint")
                    if raw_interval is None:
                        raise ValueError("stream did not provide icy-metaint")
                    decoder = IcyMetadataDecoder(int(raw_interval))
                    connected_since = monotonic()
                    print(f"{station}: connected status={response.status_code} "
                          f"metaint={decoder.metaint} "
                          f"type={response.headers.get('content-type', 'unknown')} "
                          f"url={response.url}", flush=True)
                    async for chunk in response.aiter_raw():
                        bytes_seen += len(chunk)
                        for fields in decoder.feed(chunk):
                            label = song_label(fields)
                            if label is None:
                                ignored += 1
                            elif label == previous:
                                repeats += 1
                            else:
                                previous = label
                                changes += 1
                                await queue.put((station, label, datetime.now(timezone.utc)))
                        if monotonic() >= next_report:
                            status = classify_icy_health(
                                station, blocks=blocks + decoder.blocks_seen,
                                parsed=parsed + decoder.parsed_blocks,
                                changes=changes,
                                seconds_connected=monotonic() - connected_since
                                if connected_since is not None else 0.0,
                            )
                            print(f"{station}: health status={status.status.value} bytes={bytes_seen} "
                                  f"blocks={blocks + decoder.blocks_seen} "
                                  f"empty={empty + decoder.empty_blocks} "
                                  f"parsed={parsed + decoder.parsed_blocks} "
                                  f"ignored={ignored} repeated={repeats} "
                                  f"changes={changes}", flush=True)
                            next_report = monotonic() + diagnostics_interval
                    print(f"{station}: stream ended; reconnecting", flush=True)
            except (httpx.HTTPError, ValueError, OSError) as exc:
                print(f"{station}: stream error {type(exc).__name__}: {exc}; "
                      "reconnecting", flush=True)
            finally:
                if decoder is not None:
                    blocks += decoder.blocks_seen
                    empty += decoder.empty_blocks
                    parsed += decoder.parsed_blocks
            connected_since = None
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
                  reconnect_seconds: float, diagnostics_interval: float) -> None:
    queue: asyncio.Queue[tuple[str, str, datetime]] = asyncio.Queue()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(write_events(queue, database))
        for station, url in stations:
            tasks.create_task(listen(station, url, queue, reconnect_seconds,
                                     diagnostics_interval))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", nargs=2, action="append", required=True,
                        metavar=("NAME", "URL"))
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--reconnect-seconds", type=float, default=5.0)
    parser.add_argument("--diagnostics-interval", type=float, default=60.0)
    args = parser.parse_args()
    if args.reconnect_seconds <= 0 or args.diagnostics_interval <= 0:
        parser.error("intervals must be positive")
    if len({name for name, _ in args.station}) != len(args.station):
        parser.error("station names must be unique")
    try:
        asyncio.run(collect(args.station, args.database, args.reconnect_seconds,
                            args.diagnostics_interval))
    except KeyboardInterrupt:
        print("Collector stopped.")


if __name__ == "__main__":
    main()
