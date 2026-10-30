"""Parse timestamped Netplayer recently-played HTML without network access."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser


@dataclass(frozen=True)
class PlaylistPlay:
    label: str
    played_at: datetime


class _NetplayerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.row_depth: int | None = None
        self.row_text: list[str] = []
        self.row_times: list[str] = []
        self.plays: list[PlaylistPlay] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div" and self.row_depth is None:
            classes = set((attributes.get("class") or "").split())
            if {"my-3", "row"} <= classes:
                self.row_depth = self.depth
                self.row_text = []
                self.row_times = []
        if self.row_depth is not None and tag == "time":
            timestamp = attributes.get("datetime")
            if timestamp:
                self.row_times.append(timestamp)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass

    def handle_data(self, data: str) -> None:
        if self.row_depth is not None and data.strip():
            self.row_text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            return
        self.depth = max(0, self.depth - 1)
        if tag == "div" and self.row_depth is not None and self.depth == self.row_depth:
            self._finish_row()
            self.row_depth = None

    def _finish_row(self) -> None:
        if not self.row_times:
            return
        # Song label is the first text element of the song row, ahead of
        # release dates, popularity counters and relative play times.
        label = next((value for value in self.row_text[:5] if " - " in value), None)
        if not label:
            return
        artist, title = label.split(" - ", 1)
        if not artist.strip() or not title.strip():
            return
        try:
            played_at = datetime.fromisoformat(self.row_times[0].replace("Z", "+00:00"))
        except ValueError:
            return
        if played_at.tzinfo is None:
            return
        self.plays.append(PlaylistPlay(f"{artist.strip()} - {title.strip()}", played_at.astimezone(timezone.utc)))


def parse_netplayer(html: str) -> list[PlaylistPlay]:
    """Return unique plays in chronological order; ignore header timestamps."""
    parser = _NetplayerParser()
    parser.feed(html)
    unique = {(play.played_at, play.label): play for play in parser.plays}
    return sorted(unique.values(), key=lambda play: (play.played_at, play.label))
