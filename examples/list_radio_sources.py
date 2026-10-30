"""Inspect known radio sources and health-aware eligibility."""
from musicforge.airplay.registry import DETROIT_STATIONS, choose_source


def main() -> None:
    for station in DETROIT_STATIONS:
        selection = choose_source(station)
        print(f"{station.callsign}: {selection.reason}")
        for source in sorted(station.sources, key=lambda s: s.priority):
            print(f"  {source.name} [{source.kind.value}] "
                  f"priority={source.priority} verified={source.verified}")
        if selection.source:
            print(f"  selected: {selection.source.name}")


if __name__ == "__main__":
    main()
