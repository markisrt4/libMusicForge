"""ICY framing, chunk boundaries, and music-only title parsing."""
from musicforge.airplay.icy import IcyMetadataDecoder, parse_icy_metadata, song_label


def block(text: str) -> bytes:
    payload = text.encode()
    blocks = (len(payload) + 15) // 16
    return bytes([blocks]) + payload.ljust(blocks * 16, b"\x00")


def test_decoder_chunk_boundaries():
    decoder = IcyMetadataDecoder(4)
    stream = (b"abcd" + block("StreamTitle='Shinedown - 45 (Acoustic)';") +
              b"efgh" + b"\x00" + b"ijkl" +
              block("StreamTitle='Queen - Radio Ga Ga';"))
    events = []
    for byte in stream:
        events.extend(decoder.feed(bytes([byte])))
    assert [song_label(event) for event in events] == [
        "Shinedown - 45 (Acoustic)", "Queen - Radio Ga Ga"]


def test_iheart_rich_metadata_and_sweep():
    song = parse_icy_metadata(
        b'StreamTitle=\'Lady Gaga - text="Paparazzi" song_spot="M"\';')
    assert song_label(song) == "Lady Gaga - Paparazzi"
    sweep = parse_icy_metadata(b'StreamTitle=\'Station ID - text="Promo" song_spot="T"\';')
    assert song_label(sweep) is None


def test_missing_and_invalid():
    import pytest
    with pytest.raises(ValueError):
        IcyMetadataDecoder(0)
    assert song_label({}) is None
    assert song_label({"streamtitle": "Station Ident"}) is None
