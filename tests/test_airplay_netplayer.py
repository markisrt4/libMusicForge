"""Netplayer HTML parser regression tests (no network required)."""
from datetime import datetime, timezone

from musicforge.airplay.netplayer import parse_netplayer


def _row(label: str, stamp: str) -> str:
    return (
        '<div class="my-3 row"><div class="col-12 col-sm-5">'
        f'<a>{label}</a><div>2026-03-06</div></div>'
        '<div class="col-12 col-sm-5">Popularity: 7days 14</div>'
        '<div class="col-12 col-sm-2"><span>Played</span>'
        f'<div><time dateTime="{stamp}">UTC</time></div>'
        '</div></div>'
    )


def test_parses_songs_not_station_update():
    html = (
        '<div>Playlist updated <time dateTime="2026-10-30T21:28:09.000Z">now</time></div>'
        + _row("From Ashes to New - Die for You", "2026-10-30T21:28:09.000Z")
        + _row("Linkin Park - Numb", "2026-10-30T21:24:50.000Z")
    )
    plays = parse_netplayer(html)
    assert [p.label for p in plays] == ["Linkin Park - Numb", "From Ashes to New - Die for You"]
    assert plays[1].played_at == datetime(2026, 10, 30, 21, 28, 9, tzinfo=timezone.utc)


def test_deduplicates_and_ignores_invalid_rows():
    valid = _row("Cracker - Low", "2026-10-30T21:20:25.000Z")
    html = valid + valid + _row("Missing artist", "2026-10-30T21:30:00.000Z")
    assert len(parse_netplayer(html)) == 1


def test_rejects_malformed_timestamps():
    assert parse_netplayer(_row("Cracker - Low", "not-a-date")) == []
