from musicforge.airplay import parse_media_playlist
from musicforge.airplay.diagnostics import HlsObservationTracker, diagnose_playlist


def test_gap_and_span():
    playlist = parse_media_playlist("""#EXTM3U
#EXT-X-MEDIA-SEQUENCE:10
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:00:00Z
#EXTINF:10,Artist - Track
a.aac
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:00:30Z
#EXTINF:10,Artist - Track
b.aac
""")
    diagnostics = diagnose_playlist(playlist)
    assert diagnostics.media_duration_seconds == 20
    assert diagnostics.wall_span_seconds == 40
    assert diagnostics.gaps_seconds == (20,)
    assert diagnostics.overlaps_seconds == ()


def test_overlapping_snapshot_does_not_duplicate_segment_observation():
    first = parse_media_playlist("""#EXTM3U
#EXT-X-MEDIA-SEQUENCE:20
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:00:00Z
#EXTINF:10,Artist - Track
a.aac
#EXTINF:10,Artist - Track
b.aac
""")
    second = parse_media_playlist("""#EXTM3U
#EXT-X-MEDIA-SEQUENCE:21
#EXT-X-PROGRAM-DATE-TIME:2026-10-30T06:00:10Z
#EXTINF:10,Artist - Track
b.aac
#EXTINF:10,Another - Song
c.aac
""")
    tracker = HlsObservationTracker()
    assert [s.title for s in tracker.observe("WOMC", first)] == ["Artist - Track"]
    assert [s.title for s in tracker.observe("WOMC", second)] == ["Another - Song"]
    assert tracker.observe("WOMC", second) == ()
