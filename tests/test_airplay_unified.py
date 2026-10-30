"""Unified collector selection is explicit and never runs unverified WRIF."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from collect_radio import selected_sources
from musicforge.airplay.registry import RadioSource, RadioStation, SourceKind


def test_seed_selects_three_verified_sources():
    sources = selected_sources()
    assert {name for name, _ in sources} == {"WNIC", "WOMC", "WYCD"}
    assert {source.kind for _, source in sources} == {
        SourceKind.ICY, SourceKind.HLS,
    }


def test_unimplemented_playlist_is_skipped():
    stations = (RadioStation("TEST", (
        RadioSource("feed", SourceKind.PLAYLIST,
                    "https://example.org/feed", verified=True),
    )),)
    assert selected_sources(stations) == []
