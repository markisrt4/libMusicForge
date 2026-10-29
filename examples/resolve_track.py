"""Resolve a normalized playback observation on any Python platform."""

import argparse
import asyncio
import os

from musicforge.playback import MusicBrainzNameResolver, TrackIdentity
from musicforge.providers.musicbrainz import MusicBrainzAdapter


async def run(source: str, artist: str, title: str, duration_ms: int | None) -> None:
    track = TrackIdentity(
        source=source, artist=artist, title=title, duration_ms=duration_ms
    )
    async with MusicBrainzAdapter(contact=os.environ["MUSICBRAINZ_CONTACT"]) as mb:
        result = await MusicBrainzNameResolver(mb).resolve(track)
    for candidate in result.candidates:
        ids = ", ".join(i.value for i in candidate.recording.identifiers)
        print(f"{candidate.recording.title}: {ids}")
        print(f"  evidence: {', '.join(candidate.evidence) or 'none'}")
        print(f"  duration difference: {candidate.duration_difference_ms} ms")
    print("Verified recording identity:", result.verified)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artist")
    parser.add_argument("title")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--duration-ms", type=int)
    args = parser.parse_args()
    if not os.environ.get("MUSICBRAINZ_CONTACT"):
        parser.error("Set MUSICBRAINZ_CONTACT")
    asyncio.run(run(args.source, args.artist, args.title, args.duration_ms))


if __name__ == "__main__":
    main()
