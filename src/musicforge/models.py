"""! @brief Immutable, provider-independent music domain models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Identifier:
    """! @brief Identifier in a provider's namespace (e.g. musicbrainz/recording)."""

    namespace: str
    value: str


@dataclass(frozen=True, slots=True)
class Artist:
    """! @brief Artist name and provider identifiers."""

    name: str
    identifiers: tuple[Identifier, ...] = ()


@dataclass(frozen=True, slots=True)
class Recording:
    """! @brief A recorded performance, not necessarily a particular release track."""

    title: str
    artists: tuple[Artist, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class Release:
    """! @brief A particular album/single release, distinct from its recordings."""

    title: str
    artists: tuple[Artist, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    recordings: tuple[Recording, ...] = ()


@dataclass(frozen=True, slots=True)
class Statistic:
    """! @brief Source-specific observation; values are never assumed comparable."""

    provider: str
    metric: str
    value: int | float
    observed_at: datetime
    unit: str
    subject: Identifier
