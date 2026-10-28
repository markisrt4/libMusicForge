"""Last.fm artist and track statistics via the public API.

The metrics are Last.fm scrobbles/listeners, never Spotify stream counts.
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from musicforge.models import Identifier, Statistic

_API_URL = "https://ws.audioscrobbler.com/2.0/"


class LastFmError(RuntimeError):
    """Last.fm API request or response failed."""


class LastFmAdapter:
    """Read-only Last.fm statistics provider.

    Provide an API key via configuration; never embed credentials in source.
    The client is closed only if the adapter created it.
    """

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Last.fm API key must not be empty")
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._owns_client = client is None

    async def __aenter__(self) -> "LastFmAdapter":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, **params: str) -> dict[str, Any]:
        try:
            response = await self._client.get(
                _API_URL,
                params={
                    "method": method,
                    "api_key": self._api_key,
                    "format": "json",
                    "autocorrect": "0",
                    **params,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LastFmError("Last.fm request failed") from exc
        if not isinstance(payload, dict):
            raise LastFmError("Last.fm returned an invalid response")
        if "error" in payload:
            raise LastFmError(
                f"Last.fm API error {payload['error']}: {payload.get('message', 'unknown error')}"
            )
        return payload

    async def artist_statistics(self, artist: str) -> list[Statistic]:
        """Get global Last.fm listener and scrobble totals for an artist."""
        if not artist.strip():
            raise ValueError("artist must not be empty")
        payload = await self._request("artist.getinfo", artist=artist)
        data = payload.get("artist")
        if not isinstance(data, dict):
            raise LastFmError("Last.fm artist response missing artist")
        stats = data.get("stats")
        if not isinstance(stats, dict):
            raise LastFmError("Last.fm artist response missing stats")
        subject = Identifier("lastfm:artist", str(data.get("name") or artist))
        return _statistics(stats, subject, {"listeners": "listeners", "playcount": "scrobbles"})

    async def track_statistics(self, artist: str, title: str) -> list[Statistic]:
        """Get global Last.fm listener and scrobble totals for a track."""
        if not artist.strip() or not title.strip():
            raise ValueError("artist and title must not be empty")
        payload = await self._request("track.getInfo", artist=artist, track=title)
        data = payload.get("track")
        if not isinstance(data, dict):
            raise LastFmError("Last.fm track response missing track")
        actual_artist = data.get("artist")
        artist_name = actual_artist.get("name") if isinstance(actual_artist, dict) else artist
        subject = Identifier(
            "lastfm:track",
            f"{artist_name}::{data.get('name') or title}",
        )
        return _statistics(data, subject, {"listeners": "listeners", "playcount": "scrobbles"})


def _statistics(
    data: dict[str, Any],
    subject: Identifier,
    metrics: dict[str, str],
) -> list[Statistic]:
    observed_at = datetime.now(timezone.utc)
    results: list[Statistic] = []
    for field, unit in metrics.items():
        raw = data.get(field)
        if raw is None:
            continue
        try:
            count = int(raw)
        except (TypeError, ValueError) as exc:
            raise LastFmError(f"Invalid Last.fm {field} count") from exc
        if isinstance(raw, bool) or count < 0:
            raise LastFmError(f"Invalid Last.fm {field} count")
        results.append(
            Statistic(
                provider="lastfm",
                metric="global_listener_count" if field == "listeners" else "global_scrobble_count",
                value=count,
                observed_at=observed_at,
                unit=unit,
                subject=subject,
            )
        )
    return results
