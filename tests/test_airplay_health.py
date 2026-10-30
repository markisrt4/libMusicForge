from musicforge.airplay.health import SourceStatus, classify_icy_health


def health(blocks=0, parsed=0, changes=0, seconds=120, error=None):
    return classify_icy_health("WRIF", blocks=blocks, parsed=parsed,
                               changes=changes, seconds_connected=seconds,
                               error=error).status


def test_warmup_does_not_false_alarm():
    assert health(blocks=50, seconds=30) == SourceStatus.CONNECTING


def test_all_empty_metadata_is_unhealthy():
    assert health(blocks=266) == SourceStatus.EMPTY_METADATA


def test_unrecognized_metadata_is_distinct():
    assert health(blocks=50, parsed=2) == SourceStatus.NO_SONGS


def test_recognized_songs_are_healthy():
    assert health(blocks=108, parsed=3, changes=2) == SourceStatus.HEALTHY


def test_explicit_errors_override_counters():
    assert health(blocks=50, parsed=2, changes=1, error="connection lost") == SourceStatus.ERROR
