"""Search MusicBrainz recordings and query separate Last.fm track statistics."""

import argparse
import asyncio
import os

from musicforge.identification import identify_and_enrich
from musicforge.providers.lastfm import LastFmAdapter
from musicforge.providers.musicbrainz import MusicBrainzAdapter, MusicBrainzError


async def run(artist: str, title: str, contact: str, api_key: str) -> None:
    async with MusicBrainzAdapter(contact=contact) as metadata:
        async with LastFmAdapter(api_key=api_key) as statistics:
            result = await identify_and_enrich(metadata, statistics, artist, title)
        details = []
        for candidate in result.candidates:
            identifier = next(
                (item for item in candidate.identifiers if item.namespace == "musicbrainz:recording"),
                None,
            )
            if identifier is None:
                details.append(None)
                continue
            try:
                details.append(await metadata.get_recording_details(identifier))
            except MusicBrainzError as exc:
                print(f"  Recording details unavailable for {identifier.value}: {exc}")
                details.append(None)
    print(f"MusicBrainz candidates for {artist} - {title}:")
    for recording, detail in zip(result.candidates, details):
        enriched = detail.recording if detail is not None else recording
        ids = ", ".join(f"{item.namespace}={item.value}" for item in enriched.identifiers)
        credits = ", ".join(a.name for a in enriched.artists) or "unknown artist"
        duration = (
            f"{enriched.duration_ms // 60000}:{(enriched.duration_ms // 1000) % 60:02d}"
            if enriched.duration_ms is not None else "unknown duration"
        )
        print(f"  {enriched.title} | {credits} | {duration}")
        print(f"    {ids}")
        if detail is not None:
            for release in detail.releases[:5]:
                print(f"    Release: {release.title} ({release.date or 'date unknown'})")
            if len(detail.releases) > 5:
                print(f"    ... and {len(detail.releases) - 5} more releases")
    if result.metadata_error:
        print(f"MusicBrainz unavailable: {result.metadata_error}")
    print("Candidate recordings are not automatically ranked or classified as live/remastered.")
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
