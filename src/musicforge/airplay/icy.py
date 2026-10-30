"""Incremental ICY metadata framing and radio title normalization.

Audio bytes are discarded. No decoding or audio recording is performed.
"""
from __future__ import annotations

import re


def parse_icy_metadata(payload: bytes) -> dict[str, str]:
    """Parse ICY key='value'; fields, tolerating quoted semicolons."""
    text = payload.rstrip(b"\x00").decode("utf-8", errors="replace")
    return {match.group(1).lower(): match.group(2) for match in
            re.finditer(r"([\w-]+)='((?:[^'\\]|\\.)*)';?", text)}


def song_label(fields: dict[str, str]) -> str | None:
    """Return artist-title for music, excluding iHeart talk/sweep metadata."""
    title = fields.get("streamtitle", "").strip()
    if not title or fields.get("song_spot", "M").upper() != "M":
        return None
    # iHeart embeds song_spot inside StreamTitle rather than as an ICY field.
    embedded_spot = re.search(r'(?:^|\s)song_spot="([^"]+)"', title, re.IGNORECASE)
    if embedded_spot and embedded_spot.group(1).upper() != "M":
        return None
    # iHeart sends: Artist - text="Title" song_spot="M" ...
    rich = re.match(r'^(.+?)\s+-\s+text="([^"]+)"', title)
    if rich:
        return f"{rich.group(1).strip()} - {rich.group(2).strip()}"
    # Some stations put metadata attributes outside StreamTitle.
    title = re.sub(r'\s+song_spot="[^"]*".*$', "", title)
    if " - " not in title:
        return None
    artist, song = title.split(" - ", 1)
    return f"{artist.strip()} - {song.strip()}" if artist.strip() and song.strip() else None


class IcyMetadataDecoder:
    """Consume arbitrary stream chunks and emit each nonempty metadata block."""

    def __init__(self, metaint: int) -> None:
        if metaint <= 0:
            raise ValueError("icy-metaint must be positive")
        self.metaint = metaint
        self._audio_left = metaint
        self._metadata_left = 0
        self._metadata = bytearray()
        self._need_length = False

    def feed(self, chunk: bytes) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        offset = 0
        while offset < len(chunk):
            if self._need_length:
                self._metadata_left = chunk[offset] * 16
                offset += 1
                self._need_length = False
                self._metadata.clear()
                if self._metadata_left == 0:
                    self._audio_left = self.metaint
                continue
            if self._metadata_left:
                count = min(self._metadata_left, len(chunk) - offset)
                self._metadata.extend(chunk[offset:offset + count])
                offset += count
                self._metadata_left -= count
                if self._metadata_left == 0:
                    fields = parse_icy_metadata(bytes(self._metadata))
                    if fields:
                        events.append(fields)
                    self._audio_left = self.metaint
                continue
            count = min(self._audio_left, len(chunk) - offset)
            offset += count
            self._audio_left -= count
            if self._audio_left == 0:
                self._need_length = True
        return events
