"""Example: Last.fm global listening statistics (requires an API key)."""

import asyncio
import os

from musicforge.providers.lastfm import LastFmAdapter


async def main() -> None:
    api_key = os.environ["LASTFM_API_KEY"]
    async with LastFmAdapter(api_key=api_key) as lastfm:
        for stat in await lastfm.track_statistics("Collective Soul", "Burn"):
            print(f"{stat.metric}: {stat.value} {stat.unit} ({stat.provider})")


if __name__ == "__main__":
    asyncio.run(main())
