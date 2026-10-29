import asyncio

import pytest

from musicforge.providers.mpd import MpdError, MpdPlaybackSource


async def scenario(
    state: str = "play", song: str = "Title: Burn\nArtist: Collective Soul\nAlbum: Home\nduration: 215.4\nfile: burn.flac\n",
    password: str | None = None, error: str | None = None,
):
    commands = []

    async def handler(reader, writer):
        writer.write(b"OK MPD 0.24.0\n")
        await writer.drain()
        try:
            while line := await reader.readline():
                command = line.decode().strip()
                commands.append(command)
                if error and command.startswith(error):
                    writer.write(b"ACK [4@0] {bad} permission denied\n")
                elif command.startswith("status"):
                    writer.write(f"state: {state}\nOK\n".encode())
                elif command.startswith("currentsong"):
                    writer.write((song + "OK\n").encode())
                else:
                    writer.write(b"OK\n")
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    async with server:
        port = server.sockets[0].getsockname()[1]
        source = MpdPlaybackSource(port=port, password=password)
        if error:
            with pytest.raises(MpdError):
                await source.current_track()
            return commands
        track = await source.current_track()
        return track, commands


def test_playing_track() -> None:
    track, commands = asyncio.run(scenario())
    assert commands == ["status", "currentsong"]
    assert track.title == "Burn"
    assert track.artist == "Collective Soul"
    assert track.album == "Home"
    assert track.duration_ms == 215400
    assert track.source_track_id == "burn.flac"


def test_stopped_does_not_fetch_song() -> None:
    track, commands = asyncio.run(scenario(state="stop"))
    assert track is None
    assert commands == ["status"]


def test_password_and_ack() -> None:
    track, commands = asyncio.run(scenario(password='pass"word'))
    assert commands[0] == 'password "pass\\"word"'
    assert track is not None
    commands = asyncio.run(scenario(password="bad", error="password"))
    assert commands == ['password "bad"']


def test_missing_tags_and_bad_duration() -> None:
    track, _ = asyncio.run(scenario(song="Title: Burn\nduration: bad\n"))
    assert track is None
    track, _ = asyncio.run(scenario(song="Title: Burn\nArtist: Collective Soul\nduration: bad\n"))
    assert track.duration_ms is None


def test_invalid_port() -> None:
    with pytest.raises(ValueError):
        MpdPlaybackSource(port=0)
