# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Headless end-to-end music analysis component check (Termux/Linux)."""
from __future__ import annotations

import numpy as np

from musicforge.analysis import MusicAnalyzer

RATE = 48_000
SIZE = 2048


def tone(hz: float, amplitude: float = 0.35) -> np.ndarray:
    time = np.arange(SIZE, dtype=np.float32) / RATE
    return (amplitude * np.sin(2 * np.pi * hz * time)).astype(np.float32)


def main() -> None:
    analyzer = MusicAnalyzer(fft_size=SIZE, band_count=24)
    silence = np.zeros(SIZE, dtype=np.float32)
    empty = analyzer.analyze(silence, RATE)
    assert empty.level == 0 and empty.beat == 0
    print("silence: level=0 beat=0")

    for frequency, band in ((70, "bass"), (1000, "mid"), (8000, "treble")):
        # Reset onset history between independently measured tones.
        analyzer.clear_zeroize()
        frame = analyzer.analyze(tone(frequency), RATE)
        peak_index = int(np.argmax(frame.spectrum_dbfs))
        peak_hz = frame.spectrum_hz[peak_index]
        resolution = RATE / SIZE
        assert abs(peak_hz - frequency) <= resolution
        assert getattr(frame, band) > 0.9
        assert len(frame.spectrum) == 24
        assert len(frame.spectrum_hz) == len(frame.spectrum_dbfs) == SIZE // 2 + 1
        print(f"{band:6s}: input={frequency:5d}Hz peak={peak_hz:8.2f}Hz "
              f"peak={frame.spectrum_dbfs[peak_index]:6.1f}dBFS")

    analyzer.clear_zeroize()
    analyzer.analyze(silence, RATE)
    onset = analyzer.analyze(tone(1000), RATE).beat
    tail = [analyzer.analyze(tone(1000), RATE).beat for _ in range(8)]
    assert onset > 0 and tail[-1] < onset
    assert all(0 <= value <= 1 for value in tail)
    print(f"onset: first={onset:.3f} sustained_after_8={tail[-1]:.3f}")

    analyzer.start_zeroize()
    for _ in range(8):
        analyzer.analyze(silence, RATE)
    analyzer.finish_zeroize()
    assert analyzer.is_zeroized
    analyzer.clear_zeroize()
    assert not analyzer.is_zeroized
    assert analyzer.analyze(tone(1000), RATE).beat == 0
    print("calibration: collect/save/clear/reset PASS")
    print("PASS: standalone libMusicForge music-analysis component test")


if __name__ == "__main__":
    main()
