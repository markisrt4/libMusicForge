# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared data types produced by music analysis backends."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PercussionActivity:
    """Normalized percussion activity estimates in the range 0.0 through 1.0."""

    kick: float = 0.0
    bass: float = 0.0
    snare: float = 0.0
    tom_high: float = 0.0
    tom_mid: float = 0.0
    tom_low: float = 0.0
    cymbal: float = 0.0


@dataclass(frozen=True)
class MusicAnalysisState:
    """Frontend-neutral snapshot of analyzed audio."""

    level: float = 0.0
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    spectrum: tuple[float, ...] = field(default_factory=tuple)
    percussion: PercussionActivity = field(default_factory=PercussionActivity)
    sample_rate_hz: int = 0
    fft_size: int = 0
