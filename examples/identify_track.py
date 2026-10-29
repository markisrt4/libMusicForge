"""Search MusicBrainz recordings and query separate Last.fm track statistics."""

import argparse
import asyncio
import os

from musicforge.identification import identify_and_enrich
from musicforge.providers.lastfm import LastFmAdapter
from musicforge.providers.musicbrainz import MusicBrainzAdapter


async def run(artist: str, title: str, contact: str, api_key: str) -> None:
    async with MusicBrainzAdapter(contact=contact) as metadata:
        async with LastFmAdapter(api_key=api_key) as statistics:
            result = await identify_and_enrich(metadata, statistics, artist, title)
    print(f"MusicBrainz candidates for {artist} - {title}:")
    for recording in result.candidates:
        ids = ", ".join(f"{item.namespace}={item.value}" for item in recording.identifiers)
        print(f"  {recording.title}: {ids}")
    if result.metadata_error:
        print(f"MusicBrainz unavailable: {result.metadata_error}")
    print("Last.fm artist/title statistics (not assigned to a specific recording):")
    for stat in result.statistics:
        print(f"  {stat.metric}: {stat.value:,} {stat.unit}")
    if result.statistics_error:
        print(f"Last.fm unavailable: {result.statistics_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up music identities and Last.fm listening counts")
    parser.add_argument("artist")
    parser.add_argument("title")
    args = parser.parse_args()
    api_key = os.getenv("LASTFM_API_KEY")
    contact = os.getenv("MUSICBRAINZ_CONTACT")
    if not api_key or not contact:
        parser.error("Set LASTFM_API_KEY and MUSICBRAINZ_CONTACT first")
    asyncio.run(run(args.artist, args.title, contact, api_key))


if __name__ == "__main__":
    main()
