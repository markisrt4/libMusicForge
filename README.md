# libMusicForge

**An open-source, library-first toolkit for music metadata, statistics, and discovery.**

libMusicForge provides a consistent way to query and reconcile music information across multiple services. It is designed for applications that need artist, recording, release, and community-listening data without coupling themselves to any one provider.

**Status:** Early development. The Python foundation and MusicBrainz adapter are implemented on development branches; provider support and public APIs may change before the first release.

## Goals

- **Library first:** A reusable Python package with an optional HTTP API, not a music player or graphical dashboard.
- **Provider independence:** No mandatory Spotify, Last.fm, or other commercial service account.
- **Normalized metadata:** Consistent artist, recording, release, and identifier models with source attribution.
- **Honest metrics:** Distinguish Spotify streams, Last.fm scrobbles, listener counts, and locally observed plays.
- **Extensibility:** Capability-specific provider adapters rather than one giant interface.
- **Practical operation:** Async I/O, caching, rate-limit handling, and graceful degradation when providers are unavailable.
- **Portable integrations:** Usable from OpenRoadCode, Linux, Raspberry Pi, Android/Termux, or independent applications.

## Non-goals

- Hosting, downloading, or distributing copyrighted audio.
- Building a music player, graphical dashboard, or ORC-specific user interface.
- Claiming exact Spotify stream counts where the source does not provide them.
- Requiring a continuously running service to use the Python library.

## Planned capabilities

| Capability | Description |
| --- | --- |
| Metadata | Artist, recording, track, release, credits, and identifiers |
| Search | Resolve and match recordings across providers |
| Statistics | Source-labeled listener counts, scrobbles, and available trends |
| Discovery | Related artists, tracks, and catalog exploration |
| Optional HTTP API | REST interface built on the same library services |
| Cache | Optional persistent caching and request throttling |

Potential providers include **MusicBrainz**, **Last.fm**, **ListenBrainz**, and **Spotify**, subject to their individual API terms, credentials, quotas, and availability. A provider's inclusion here is a roadmap item, not an implementation claim.

## Architecture (proposed)

```text
Applications (ORC, CLI, third-party clients)
           |                     |
      Python package        Optional REST API
           \                     /
            Core services and models
                       |
           Capability-based interfaces
                       |
       MusicBrainz / Last.fm / other adapters
                       |
              Optional cache/storage
```

The library remains usable without the HTTP server. Providers implement only the capabilities they support. Normalized results preserve provider IDs, attribution, metric units, and retrieval timestamps where applicable.

## Development roadmap

1. **Foundation:** Packaging, typed domain models, provider contracts, unit tests, and CI.
2. **Metadata:** MusicBrainz search and recording/release resolution.
3. **Statistics:** Last.fm metrics with clear source and semantics.
4. **Discovery:** Similar artists and related music where supported.
5. **API:** Optional versioned REST service and usage examples.
6. **Integrations:** Demonstrate consumption by OpenRoadCode without introducing ORC dependencies into the library.

## Development installation and usage

The library is not published to PyPI yet. From a checkout of the development branch:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

The `dev` extra installs only pytest, making it suitable for Termux. On Linux or CI, install the additional linting, type-checking, and build tools with `python -m pip install -e ".[dev,quality]"`. Ruff is not required for normal development or runtime use.

MusicBrainz is the first implemented provider. Use a real contact address in your User-Agent as required by MusicBrainz's API guidance:

```python
import asyncio
from musicforge import MusicForge
from musicforge.providers.musicbrainz import MusicBrainzAdapter

async def main():
    async with MusicBrainzAdapter(contact="you@example.com") as provider:
        async with MusicForge([provider]) as music:
            tracks = await music.search_track("Collective Soul", "Burn")
            for track in tracks:
                print(track.title, track.artists, track.identifiers)

asyncio.run(main())
```

Results are a list of candidate recordings, not a guaranteed unique match. The adapter uses public MusicBrainz endpoints and defaults to at least 1.1 seconds between its requests. No network calls are required for unit tests.

## Contributing

Contributions and design discussions are welcome. Please read [AGENTS.md](AGENTS.md) for repository conventions and agent-assisted development rules. Open an issue before undertaking major interface or architecture changes.

## Licensing

Licensed under the [Apache License 2.0](LICENSE).

libMusicForge is an independent open-source project. Third-party music metadata and analytics remain subject to their respective providers' terms and licenses.


## Last.fm statistics (development branch)

Last.fm provides **Last.fm listener counts and scrobbles**, not Spotify streams. A free Last.fm API key is required for the statistics adapter.

```bash
export LASTFM_API_KEY="your-api-key"
python examples/lastfm_statistics.py
```

Or use the Python API:

```python
from musicforge.providers.lastfm import LastFmAdapter

async with LastFmAdapter(api_key="your-api-key") as lastfm:
    stats = await lastfm.track_statistics("Collective Soul", "Burn")
    for stat in stats:
        print(stat.metric, stat.value, stat.unit, stat.provider)
```

The Last.fm adapter currently exposes `artist_statistics()` and `track_statistics()` directly. Cross-provider statistic lookup by shared identifiers is not implemented; Last.fm artist/track names are not interchangeable with MusicBrainz IDs. Tests use mocked HTTP and do not require an API key or network connection.

## Compare multiple tracks

Compare Last.fm listening statistics using the optional example CLI (no new dependencies):

```bash
export LASTFM_API_KEY="your-api-key"
python examples/compare_tracks.py \
  "Collective Soul:Burn" \
  "Journey:Don't Stop Believin'" \
  "Queen:Bohemian Rhapsody" \
  "Nirvana:Smells Like Teen Spirit" \
  --sort ratio
```

Supported sorting: `--sort listeners` (default), `--sort scrobbles`, or `--sort ratio`. Add `--ascending` to reverse the default descending order. The library function `musicforge.analytics.compare_tracks(provider, tracks, sort_by="listeners")` returns typed `TrackComparison` records. A ratio is undefined when listener count is zero or missing. These are Last.fm statistics only, not estimated worldwide streams.

## Cross-provider track lookup

MusicBrainz identifies recording candidates while Last.fm reports artist/title-level listening totals. The library **does not** claim that Last.fm statistics belong to any one MusicBrainz recording.

```bash
export LASTFM_API_KEY="your-api-key"
export MUSICBRAINZ_CONTACT="you@example.com"
python examples/identify_track.py "Collective Soul" "Burn"
```

Programmatic entry point: `musicforge.identification.identify_and_enrich(metadata, statistics, artist, title)`. It returns `EnrichedTrack` with all MusicBrainz candidates, separate Last.fm statistics, and `verified_recording_match=False`. Future work can introduce explicit identifier-based matching when supported by providers.
