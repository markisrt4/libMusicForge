"""Counters include empty metadata blocks, not just song-bearing blocks."""
from musicforge.airplay.icy import IcyMetadataDecoder


def test_counts_empty_and_parsed_metadata_blocks():
    decoder = IcyMetadataDecoder(2)
    text = b"StreamTitle='Queen - Radio Ga Ga';"
    blocks = (len(text) + 15) // 16
    stream = (b"ab" + b"\x00" + b"cd" +
              bytes([blocks]) + text.ljust(blocks * 16, b"\x00"))
    events = []
    for part in (stream[:3], stream[3:8], stream[8:]):
        events.extend(decoder.feed(part))
    assert decoder.blocks_seen == 2
    assert decoder.empty_blocks == 1
    assert decoder.parsed_blocks == 1
    assert events == [{"streamtitle": "Queen - Radio Ga Ga"}]
