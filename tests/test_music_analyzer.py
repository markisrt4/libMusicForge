# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the FFT-based music analyzer."""
from __future__ import annotations

import numpy as np
import pytest

from musicforge.analysis import MusicAnalyzer


_SAMPLE_RATE_HZ = 48_000
_FFT_SIZE = 2048


def _tone(frequency_hz: float, amplitude: float = 0.25) -> np.ndarray:
    samples = np.arange(_FFT_SIZE, dtype=np.float32) / _SAMPLE_RATE_HZ
    return (amplitude * np.sin(2.0 * np.pi * frequency_hz * samples)).astype(np.float32)


def test_constructor_rejects_invalid_fft_size() -> None:
    with pytest.raises(ValueError):
        MusicAnalyzer(fft_size=1000)
    with pytest.raises(ValueError):
        MusicAnalyzer(fft_size=128)


def test_constructor_rejects_too_few_bands() -> None:
    with pytest.raises(ValueError):
        MusicAnalyzer(band_count=2)


def test_analyze_rejects_invalid_sample_rate() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE)
    with pytest.raises(ValueError):
        analyzer.analyze(_tone(60.0), 0)


@pytest.mark.parametrize(
    ("frequency_hz", "dominant"),
    ((60.0, "bass"), (1000.0, "mid"), (8000.0, "treble")),
)
def test_clean_tone_has_expected_dominant_summary_band(
    frequency_hz: float,
    dominant: str,
) -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE)
    state = analyzer.analyze(_tone(frequency_hz), _SAMPLE_RATE_HZ)
    values = {"bass": state.bass, "mid": state.mid, "treble": state.treble}

    assert values[dominant] > 0.9
    for name, value in values.items():
        if name != dominant:
            assert value < 0.1


def test_sixty_hertz_tone_does_not_trigger_snare_or_cymbal() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE)
    state = analyzer.analyze(_tone(60.0), _SAMPLE_RATE_HZ)

    assert state.percussion.kick > 0.9
    assert state.percussion.snare < 0.1
    assert state.percussion.cymbal < 0.1


def test_silence_is_zero() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE)
    state = analyzer.analyze(np.zeros(_FFT_SIZE, dtype=np.float32), _SAMPLE_RATE_HZ)

    assert state.level == 0.0
    assert state.bass == 0.0
    assert state.mid == 0.0
    assert state.treble == 0.0
    assert all(value == 0.0 for value in state.spectrum)
    assert all(
        value == 0.0
        for value in (
            state.percussion.kick,
            state.percussion.bass,
            state.percussion.snare,
            state.percussion.tom_high,
            state.percussion.tom_mid,
            state.percussion.tom_low,
            state.percussion.cymbal,
        )
    )


def test_spectrum_has_requested_shape_and_range() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE, band_count=24)
    state = analyzer.analyze(_tone(1000.0), _SAMPLE_RATE_HZ)

    assert len(state.spectrum) == 24
    assert all(0.0 <= value <= 1.0 for value in state.spectrum)


def test_zeroize_requires_samples_and_can_be_cleared() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE)

    with pytest.raises(RuntimeError):
        analyzer.finish_zeroize()

    analyzer.start_zeroize()
    for _ in range(4):
        analyzer.analyze(np.zeros(_FFT_SIZE, dtype=np.float32), _SAMPLE_RATE_HZ)
    analyzer.finish_zeroize()

    assert analyzer.is_zeroized
    analyzer.clear_zeroize()
    assert not analyzer.is_zeroized


def test_low_sample_rate_returns_empty_spectrum_safely() -> None:
    analyzer = MusicAnalyzer(fft_size=_FFT_SIZE, band_count=24)
    state = analyzer.analyze(np.zeros(_FFT_SIZE, dtype=np.float32), 60)

    assert state.spectrum == tuple(0.0 for _ in range(24))
