"""Read MPD's current track on a Raspberry Pi or Linux host."""

import argparse
import asyncio
import os

from musicforge.providers.mpd import MpdPlaybackSource


async def run(host: str, port: int, password: str | None) -> None:
    track = await MpdPlaybackSource(host=host, port=port, password=password).current_track()
    if track is None:
        print("No current MPD track (stopped or missing artist/title tags)")
    else:
        print(f"{track.artist} - {track.title}")
        print(f"Album: {track.album or 'unknown'}")
        print(f"Duration: {track.duration_ms} ms")
        print(f"Source: {track.source}, file: {track.source_track_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6600)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, os.getenv("MPD_PASSWORD")))


if __name__ == "__main__":
    main()
