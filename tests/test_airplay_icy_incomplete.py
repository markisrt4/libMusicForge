from musicforge.airplay.icy import song_label, song_rejection_reason, safe_icy_title


def test_truncated_rich_title_is_rejected():
    fields = {"streamtitle": 'Phil Collins - text="You Can'}
    assert song_label(fields) is None
    assert song_rejection_reason(fields) == "incomplete_rich_title"


def test_complete_rich_title_is_accepted():
    fields = {"streamtitle": 'Phil Collins - text="You Can Call Me Al" song_spot="M"'}
    assert song_label(fields) == "Phil Collins - You Can Call Me Al"


def test_ad_context_does_not_leak_in_diagnostics():
    assert safe_icy_title({"streamtitle": 'adContext="encoded-sensitive-payload"'}) == "[advertising metadata]"
