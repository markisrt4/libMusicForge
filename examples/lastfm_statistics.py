"""Query Last.fm global track statistics using artist and song arguments."""

import argparse
import asyncio
import os

from musicforge.providers.lastfm import LastFmAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Look up Last.fm track statistics")
    parser.add_argument("artist", nargs="?", default="Collective Soul")
    parser.add_argument("title", nargs="?", default="Burn")
    return parser.parse_args()


async def main(artist: str, title: str) -> None:
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        raise SystemExit("Set LASTFM_API_KEY before running this example.")
    async with LastFmAdapter(api_key=api_key) as lastfm:
        print(f"{artist} - {title}")
        for stat in await lastfm.track_statistics(artist, title):
            print(f"{stat.metric}: {stat.value:,} {stat.unit} ({stat.provider})")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.artist, args.title))
