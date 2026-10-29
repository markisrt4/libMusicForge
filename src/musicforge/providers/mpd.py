"""Dependency-free asynchronous MPD playback observer.

Reads MPD's line protocol over TCP. This adapter never controls playback.
"""

import asyncio
from contextlib import suppress

from musicforge.playback import TrackIdentity


class MpdError(RuntimeError):
    """MPD protocol, connection or authentication failure."""


class MpdPlaybackSource:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 6600,
        password: str | None = None, timeout: float = 5.0,
    ) -> None:
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.host, self.port, self.password, self.timeout = host, port, password, timeout

    async def current_track(self) -> TrackIdentity | None:
        """Return the playing or paused track; None when stopped or unavailable.

        Connection/protocol failures raise MpdError rather than being mistaken
        for a stopped player.
        """
        try:
            return await asyncio.wait_for(self._query(), timeout=self.timeout)
        except (OSError, asyncio.TimeoutError, UnicodeError) as exc:
            raise MpdError(f"MPD connection failed: {exc}") from exc

    async def _query(self) -> TrackIdentity | None:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            greeting = await reader.readline()
            if not greeting.startswith(b"OK MPD "):
                raise MpdError("Invalid MPD greeting")
            if self.password is not None:
                await self._command(reader, writer, "password", self.password)
            status = await self._command(reader, writer, "status")
            if status.get("state", ["stop"])[0] == "stop":
                return None
            song = await self._command(reader, writer, "currentsong")
            if not song:
                return None
            title = _first(song, "Title")
            artist = _first(song, "Artist") or _first(song, "AlbumArtist")
            if not title or not artist:
                return None
            duration_ms = None
            duration = _first(song, "duration") or _first(song, "Time")
            if duration:
                try:
                    duration_ms = round(float(duration) * 1000)
                except ValueError:
                    pass
            return TrackIdentity(
                source="mpd", title=title, artist=artist,
                album=_first(song, "Album"), duration_ms=duration_ms,
                source_track_id=_first(song, "file"),
            )
        finally:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()

    async def _command(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
        command: str, argument: str | None = None,
    ) -> dict[str, list[str]]:
        line = command
        if argument is not None:
            # MPD quoted arguments require backslash and quote escaping.
            escaped = argument.replace("\\", "\\\\").replace('"', '\\"')
            line += f' "{escaped}"'
        writer.write((line + "\n").encode("utf-8"))
        await writer.drain()
        result: dict[str, list[str]] = {}
        while True:
            raw = await reader.readline()
            if not raw:
                raise MpdError("MPD disconnected mid-response")
            decoded = raw.decode("utf-8").rstrip("\r\n")
            if decoded == "OK":
                return result
            if decoded.startswith("ACK "):
                raise MpdError(f"MPD rejected {command}: {decoded}")
            if ": " not in decoded:
                raise MpdError(f"Malformed MPD response: {decoded}")
            key, value = decoded.split(": ", 1)
            result.setdefault(key, []).append(value)


def _first(data: dict[str, list[str]], key: str) -> str | None:
    values = data.get(key)
    return values[0] if values else None
