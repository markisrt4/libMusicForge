"""Compare Last.fm tracks from the command line.

Usage:
    python examples/compare_tracks.py "Journey:Don't Stop Believin'" "Queen:Bohemian Rhapsody"
"""

import argparse
import asyncio
import os

from musicforge.analytics import TrackComparison, compare_tracks
from musicforge.providers.lastfm import LastFmAdapter, LastFmError


def parse_track(value: str) -> tuple[str, str]:
    artist, sep, title = value.partition(":")
    if not sep or not artist.strip() or not title.strip():
        raise argparse.ArgumentTypeError(
            "Track must use ARTIST:TITLE, e.g. 'Queen:Bohemian Rhapsody'"
        )
    return artist.strip(), title.strip()


def display_count(value: int | None) -> str:
    return f"{value:,}" if value is not None else "N/A"


def display_ratio(track: TrackComparison) -> str:
    value = track.scrobbles_per_listener
    return f"{value:.2f}" if value is not None else "N/A"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Last.fm track statistics")
    parser.add_argument("tracks", nargs="+", type=parse_track, metavar="ARTIST:TITLE")
    parser.add_argument(
        "--sort", choices=("listeners", "scrobbles", "ratio"),
        default="listeners", help="Comparison order (default: listeners)"
    )
    parser.add_argument(
        "--ascending", action="store_true", help="Sort smallest values first"
    )
    args = parser.parse_args()
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        parser.error("Set LASTFM_API_KEY before running this example")

    async def run() -> list[TrackComparison]:
        async with LastFmAdapter(api_key=api_key) as provider:
            return await compare_tracks(
                provider, args.tracks,
                sort_by=args.sort, descending=not args.ascending
            )

    try:
        results = asyncio.run(run())
    except LastFmError as exc:
        parser.exit(1, f"Last.fm error: {exc}\n")
    print(f"{'Track':45} {'Listeners':>13} {'Scrobbles':>13} {'Per listener':>13}")
    print("-" * 88)
    for item in results:
        name = f"{item.artist} - {item.title}"
        if len(name) > 45:
            name = name[:42] + "..."
        print(
            f"{name:45} {display_count(item.listeners):>13} "
            f"{display_count(item.scrobbles):>13} {display_ratio(item):>13}"
        )
    print("\nSource: Last.fm; counts are scrobbles, not Spotify streams.")


if __name__ == "__main__":
    main()
