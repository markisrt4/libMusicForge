"""Inspect Audacy-style HLS playlist coverage without downloading audio.

Use only with endpoints you are permitted to query. Runs once, no polling.
"""
from __future__ import annotations

import argparse
import asyncio
from urllib.parse import urljoin

import httpx

from musicforge.airplay import parse_media_playlist, song_observations


async def inspect(name: str, url: str) -> None:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        master = await client.get(url)
        master.raise_for_status()
        lines = [s.strip() for s in master.text.splitlines() if s.strip()]
        if any(s.startswith("#EXT-X-STREAM-INF:") for s in lines):
            candidates = [s for s in lines if not s.startswith("#")]
            if not candidates:
                raise ValueError("Master playlist has no variants")
            url = urljoin(str(master.url), candidates[0])
            response = await client.get(url)
            response.raise_for_status()
            body = response.text
        else:
            body = master.text
    playlist = parse_media_playlist(body)
    print(f"{name}: {len(playlist.segments)} segments, "
          f"{playlist.duration_seconds:.1f}s playlist coverage, "
          f"{playlist.timestamped_duration_seconds:.1f}s timestamped")
    if playlist.segments:
        print(f"  first={playlist.segments[0].started_at} "
              f"last={playlist.segments[-1].started_at}")
    for event in song_observations(playlist):
        print(f"  candidate: {event.started_at} {event.title}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", action="append", nargs=2,
                        metavar=("NAME", "URL"), required=True)
    args = parser.parse_args()
    for name, url in args.station:
        try:
            await inspect(name, url)
        except (httpx.HTTPError, ValueError) as exc:
            print(f"{name}: ERROR: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
