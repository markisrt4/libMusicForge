"""Run verified ICY and HLS stations together with one SQLite writer.

Example: python examples/collect_radio.py --interval 30
WRIF is explicitly skipped until a metadata-capable source is verified.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from time import monotonic

import httpx

from musicforge.airplay import parse_media_playlist
from musicforge.airplay.diagnostics import HlsObservationTracker
from musicforge.airplay.registry import (
    DETROIT_STATIONS, RadioStation, SourceKind, choose_source,
)
from musicforge.airplay.storage import AirplayStore

from collect_radio_hls import fetch_playlist
from collect_radio_icy import listen as listen_icy


# Sequence is meaningful for HLS, and only process-local for ICY.
Observation = tuple[str, str, datetime, int | None, str]


async def collect_hls(
    station: str, url: str, queue: asyncio.Queue[Observation],
    interval: float,
) -> None:
    tracker = HlsObservationTracker()
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        while True:
            started = monotonic()
            try:
                playlist = parse_media_playlist(await fetch_playlist(client, url))
                for segment in tracker.observe(station, playlist):
                    if segment.started_at is not None:
                        await queue.put((station, segment.title, segment.started_at,
                                         segment.sequence, "hls"))
            except (httpx.HTTPError, ValueError) as exc:
                print(f"{station}: HLS error {type(exc).__name__}: {exc}", flush=True)
            await asyncio.sleep(max(0.0, interval - (monotonic() - started)))


async def forward_icy(
    station: str, url: str, queue: asyncio.Queue[Observation],
    reconnect_seconds: float, diagnostics_interval: float,
) -> None:
    icy_queue: asyncio.Queue[tuple[str, str, datetime]] = asyncio.Queue()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(listen_icy(station, url, icy_queue,
                                     reconnect_seconds, diagnostics_interval))
        async def forward() -> None:
            while True:
                name, label, when = await icy_queue.get()
                await queue.put((name, label, when, None, "icy"))
                icy_queue.task_done()
        tasks.create_task(forward())


async def write_observations(
    queue: asyncio.Queue[Observation], database: str,
) -> None:
    counters: dict[str, int] = {}
    with AirplayStore(database) as store:
        while True:
            station, label, when, sequence, source = await queue.get()
            try:
                if sequence is None:
                    counters[station] = counters.get(station, 0) + 1
                    sequence = counters[station]
                if store.add(station, label, when, sequence, source=source):
                    print(f"{station} [{source}]: {when.isoformat()} {label}",
                          flush=True)
            finally:
                queue.task_done()


def selected_sources(stations: tuple[RadioStation, ...] = DETROIT_STATIONS):
    """Return only verified, currently eligible sources."""
    result = []
    for station in stations:
        selection = choose_source(station)
        if selection.source is None:
            print(f"{station.callsign}: SKIPPED ({selection.reason})", flush=True)
            continue
        if selection.source.kind is SourceKind.PLAYLIST:
            print(f"{station.callsign}: SKIPPED (playlist adapter not implemented)",
                  flush=True)
            continue
        result.append((station.callsign, selection.source))
    return result


async def collect(database: str, interval: float,
                  reconnect_seconds: float, diagnostics_interval: float) -> None:
    sources = selected_sources()
    if not sources:
        raise RuntimeError("no supported verified radio sources")
    queue: asyncio.Queue[Observation] = asyncio.Queue()
    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(write_observations(queue, database))
        for station, source in sources:
            print(f"{station}: starting {source.kind.value} ({source.name})",
                  flush=True)
            if source.kind is SourceKind.ICY:
                tasks.create_task(forward_icy(
                    station, source.url, queue, reconnect_seconds,
                    diagnostics_interval))
            elif source.kind is SourceKind.HLS:
                tasks.create_task(collect_hls(station, source.url, queue, interval))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="airplay.sqlite3")
    parser.add_argument("--interval", type=float, default=30.0,
                        help="HLS polling interval in seconds")
    parser.add_argument("--reconnect-seconds", type=float, default=5.0)
    parser.add_argument("--diagnostics-interval", type=float, default=60.0)
    args = parser.parse_args()
    if args.interval < 10 or args.reconnect_seconds <= 0 or args.diagnostics_interval <= 0:
        parser.error("HLS interval must be >=10; other intervals must be positive")
    try:
        asyncio.run(collect(args.database, args.interval,
                            args.reconnect_seconds, args.diagnostics_interval))
    except KeyboardInterrupt:
        print("Unified collector stopped.")


if __name__ == "__main__":
    main()
