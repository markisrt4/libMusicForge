# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Frontend-neutral music analyzer interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .types import MusicAnalysisState


class MusicAnalyzerIf(ABC):
    """! @brief Analyze PCM samples into a frontend-neutral music state. """

    @abstractmethod
    def analyze(
        self,
        samples: Sequence[float],
        sample_rate_hz: int,
    ) -> MusicAnalysisState:
        """!
        @brief Analyze one block of normalized mono PCM samples.
        @param self The analyzer instance.
        @param samples Normalized mono PCM samples.
        @param sample_rate_hz Source sample rate in hertz.
        @return Complete analysis state for the block.
        """
        raise NotImplementedError

    @abstractmethod
    def start_zeroize(self) -> None:
        """!
        @brief Begin collecting ambient-noise calibration blocks.
        @param self The analyzer instance.
        """
        raise NotImplementedError

    @abstractmethod
    def finish_zeroize(self) -> None:
        """!
        @brief Commit the collected ambient-noise calibration.
        @param self The analyzer instance.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_zeroize(self) -> None:
        """!
        @brief Discard the current ambient-noise calibration.
        @param self The analyzer instance.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_zeroized(self) -> bool:
        """!
        @brief Return whether an ambient-noise calibration is active.
        @param self The analyzer instance.
        @return True when zeroization has been committed.
        """
        raise NotImplementedError
