from musicforge.airplay.health import SourceStatus, classify_icy_health


def test_recent_song_is_healthy():
    result = classify_icy_health("WNIC", blocks=200, parsed=3, changes=2,
                                 seconds_connected=1200, seconds_since_song=60)
    assert result.status == SourceStatus.HEALTHY


def test_old_song_does_not_keep_station_healthy_forever():
    result = classify_icy_health("WNIC", blocks=200, parsed=3, changes=2,
                                 seconds_connected=1200, seconds_since_song=901)
    assert result.status == SourceStatus.STALE


def test_nonmusic_without_song_is_not_empty_metadata():
    result = classify_icy_health("WNIC", blocks=52, parsed=1, changes=0,
                                 seconds_connected=120)
    assert result.status == SourceStatus.NO_SONGS
