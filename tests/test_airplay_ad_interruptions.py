from musicforge.airplay import parse_media_playlist
from musicforge.airplay.diagnostics import HlsObservationTracker


def test_ad_segment_does_not_duplicate_same_song():
    tracker = HlsObservationTracker()
    first = parse_media_playlist("""#EXTM3U
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:22:00Z
#EXTINF:10,Artist - Song
a.aac
#EXTINF:10,https://ads.example/banner
b.aac
""")
    second = parse_media_playlist("""#EXTM3U
#EXT-X-MEDIA-SEQUENCE:102
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:22:20Z
#EXTINF:10,
c.aac
#EXTINF:10,Artist - Song
d.aac
#EXTINF:10,Next Artist - Next Song
e.aac
""")
    assert [s.title for s in tracker.observe("WYCD", first)] == ["Artist - Song"]
    assert [s.title for s in tracker.observe("WYCD", second)] == ["Next Artist - Next Song"]
