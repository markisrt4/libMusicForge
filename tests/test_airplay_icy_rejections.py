from musicforge.airplay.icy import song_rejection_reason, safe_icy_title


def test_nonmusic_marker_is_explained():
    fields = {"streamtitle": 'Station - text="Promo" song_spot="T"'}
    assert song_rejection_reason(fields) == "nonmusic_marker"


def test_empty_title_is_explained():
    assert song_rejection_reason({}) == "missing_title"


def test_unknown_format_is_explained():
    assert song_rejection_reason({"streamtitle": "Station identifier"}) == "unrecognized_format"


def test_music_has_no_rejection():
    assert song_rejection_reason({"streamtitle": "Toto - Africa"}) is None


def test_diagnostic_title_is_bounded_and_cleaned():
    title = safe_icy_title({"streamtitle": 'Hello\nWorld song_spot="T" token=secret'}, 20)
    assert title == "Hello World"
