"""Async MusicBrainz search and lookup adapter.

Uses the public MusicBrainz JSON API. Supply a descriptive contact email in
the User-Agent and respect MusicBrainz's published rate-limit requirements.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import UUID

import httpx

from musicforge.models import Artist, Identifier, Recording, Release

_BASE_URL = "https://musicbrainz.org/ws/2"
_RETRYABLE = {429, 502, 503, 504}


class MusicBrainzError(RuntimeError):
    """MusicBrainz request or response could not be processed."""


@dataclass(frozen=True, slots=True)
class ReleaseSummary:
    title: str
    date: str | None
    identifier: Identifier


@dataclass(frozen=True, slots=True)
class RecordingDetails:
    recording: Recording
    releases: tuple[ReleaseSummary, ...] = ()


class MusicBrainzAdapter:
    """MusicBrainz metadata provider with serialized, throttled requests.

    Instances own their HTTP client unless one is supplied for testing.
    Use as an async context manager or call aclose() when finished.
    """

    def __init__(
        self,
        *,
        contact: str,
        app_name: str = "libMusicForge",
        app_version: str = "0.1.0",
        client: httpx.AsyncClient | None = None,
        min_interval: float = 1.1,
        max_retries: int = 2,
    ) -> None:
        if not contact.strip():
            raise ValueError("MusicBrainz requires a nonempty contact address")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if min_interval < 0:
            raise ValueError("min_interval must not be negative")
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._owns_client = client is None
        self._user_agent = f"{app_name}/{app_version} ({contact})"
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._lock = asyncio.Lock()
        self._last_request: float | None = None

    async def __aenter__(self) -> "MusicBrainzAdapter":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        async with self._lock:
            loop = asyncio.get_running_loop()
            for attempt in range(self._max_retries + 1):
                if self._last_request is not None:
                    wait = self._min_interval - (loop.time() - self._last_request)
                    if wait > 0:
                        await asyncio.sleep(wait)
                self._last_request = loop.time()
                try:
                    response = await self._client.get(
                        f"{_BASE_URL}/{path}",
                        params={**params, "fmt": "json"},
                        headers={"User-Agent": self._user_agent},
                    )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPStatusError as exc:
                    if (
                        exc.response.status_code in _RETRYABLE
                        and attempt < self._max_retries
                    ):
                        delay = min(2.0 * (2 ** attempt), 15.0)
                        retry_after = exc.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after))
                            except ValueError:
                                try:
                                    when = parsedate_to_datetime(retry_after)
                                    delay = max(
                                        delay,
                                        (when - datetime.now(timezone.utc)).total_seconds(),
                                    )
                                except (TypeError, ValueError, OverflowError):
                                    pass
                        await asyncio.sleep(max(0.0, min(delay, 60.0)))
                        continue
                    raise MusicBrainzError(
                        f"MusicBrainz HTTP {exc.response.status_code}"
                    ) from exc
                except (httpx.TransportError, ValueError) as exc:
                    if isinstance(exc, httpx.TransportError) and attempt < self._max_retries:
                        await asyncio.sleep(min(2.0 * (2 ** attempt), 15.0))
                        continue
                    raise MusicBrainzError(f"MusicBrainz request failed: {exc}") from exc
                if not isinstance(payload, dict):
                    raise MusicBrainzError("MusicBrainz returned a non-object response")
                return payload
            raise AssertionError("unreachable retry state")

    async def search_recordings(self, artist: str, title: str) -> list[Recording]:
        """Search recordings; results may represent multiple performances."""
        if not artist.strip() or not title.strip():
            raise ValueError("artist and title are required")
        query = f'recording:"{_escape(title)}" AND artist:"{_escape(artist)}"'
        data = await self._get("recording", {"query": query, "limit": "25"})
        return [_recording(item) for item in data.get("recordings", [])
                if isinstance(item, dict) and item.get("title")]

    async def get_recording_details(self, identifier: Identifier) -> "RecordingDetails | None":
        """Fetch release context for a specific MusicBrainz recording."""
        _validate(identifier, "recording")
        try:
            data = await self._get(
                f"recording/{identifier.value}", {"inc": "artist-credits+releases"}
            )
        except MusicBrainzError as exc:
            if _is_not_found(exc):
                return None
            raise
        releases = tuple(
            ReleaseSummary(
                title=str(item.get("title", "")),
                date=str(item.get("date", "")) or None,
                identifier=Identifier("musicbrainz:release", str(item["id"])),
            )
            for item in data.get("releases", [])
            if isinstance(item, dict) and item.get("id") and item.get("title")
        )
        return RecordingDetails(recording=_recording(data), releases=releases)

    async def get_recording(self, identifier: Identifier) -> Recording | None:
        _validate(identifier, "recording")
        try:
            data = await self._get(
                f"recording/{identifier.value}", {"inc": "artist-credits"}
            )
        except MusicBrainzError as exc:
            if _is_not_found(exc):
                return None
            raise
        return _recording(data)

    async def get_release(self, identifier: Identifier) -> Release | None:
        _validate(identifier, "release")
        try:
            data = await self._get(
                f"release/{identifier.value}", {"inc": "artist-credits+recordings"}
            )
        except MusicBrainzError as exc:
            if _is_not_found(exc):
                return None
            raise
        artists = _artists(data.get("artist-credit", []))
        recordings = tuple(
            _recording(track["recording"])
            for medium in data.get("media", [])
            if isinstance(medium, dict)
            for track in medium.get("tracks", [])
            if isinstance(track, dict) and isinstance(track.get("recording"), dict)
        )
        return Release(
            title=str(data.get("title", "")),
            artists=artists,
            identifiers=(Identifier("musicbrainz:release", identifier.value),),
            recordings=recordings,
        )


def _is_not_found(exc: MusicBrainzError) -> bool:
    return isinstance(exc.__cause__, httpx.HTTPStatusError) and exc.__cause__.response.status_code == 404


def _validate(identifier: Identifier, kind: str) -> None:
    if identifier.namespace != f"musicbrainz:{kind}":
        raise ValueError(f"Expected musicbrainz:{kind} identifier")
    # Do not allow arbitrary path segments from caller-supplied identifiers.
    try:
        UUID(identifier.value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("MusicBrainz identifiers must be UUIDs") from exc


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _artists(credits: object) -> tuple[Artist, ...]:
    if not isinstance(credits, list):
        return ()
    result: list[Artist] = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        artist = credit.get("artist")
        if isinstance(artist, dict):
            identifier = artist.get("id")
            result.append(Artist(
                name=str(artist.get("name", "")),
                identifiers=(Identifier("musicbrainz:artist", str(identifier)),)
                if identifier else (),
            ))
    return tuple(result)


def _recording(data: dict[str, Any]) -> Recording:
    identifier = data.get("id")
    duration = data.get("length")
    return Recording(
        title=str(data.get("title", "")),
        artists=_artists(data.get("artist-credit", [])),
        identifiers=(Identifier("musicbrainz:recording", str(identifier)),)
        if identifier else (),
        duration_ms=duration if isinstance(duration, int) and not isinstance(duration, bool) else None,
    )
