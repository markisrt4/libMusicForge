from musicforge.airplay import parse_media_playlist, song_observations


def test_playlist_history_and_song_deduplication():
    text = """#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:17
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T04:00:00Z
#EXTINF:10.0,https://example.com/banner
a.aac
#EXTINF:10.0,Survivor - Eye Of The Tiger
b.aac
#EXTINF:10.0,
c.aac
#EXTINF:10.0,Survivor - Eye Of The Tiger
d.aac
#EXTINF:10.0,Journey - Separate Ways
e.aac
#EXTINF:10.0,Journey - Separate Ways
f.aac
"""
    playlist = parse_media_playlist(text)
    assert len(playlist.segments) == 6
    assert playlist.duration_seconds == 60
    assert playlist.segments[0].sequence == 17
    assert playlist.segments[-1].sequence == 22
    assert playlist.segments[-1].started_at.isoformat() == "2026-10-30T04:00:50+00:00"
    titles = [s.title for s in song_observations(playlist)]
    assert titles == ["Survivor - Eye Of The Tiger", "Survivor - Eye Of The Tiger", "Journey - Separate Ways"]


def test_master_playlist_is_rejected():
    try:
        parse_media_playlist("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=128000\na.m3u8")
    except ValueError as exc:
        assert "master" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
