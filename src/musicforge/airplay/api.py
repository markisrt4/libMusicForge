"""FastAPI application factory for MusicForge observed airplay."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query

from .charts import chart, stations

DETROIT = ZoneInfo("America/Detroit")


def create_app(database: str | Path = "airplay.sqlite3") -> FastAPI:
    app = FastAPI(title="MusicForge Airplay API", version="1.0.0")
    db = Path(database)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok" if db.is_file() else "unavailable", "database_available": db.is_file()}

    @app.get("/api/v1/stations")
    def list_stations() -> dict:
        if not db.is_file():
            raise HTTPException(503, "Airplay database unavailable")
        return {"stations": stations(db)}

    def get_chart(kind: str, station: str | None, period: str, limit: int, day: date | None) -> dict:
        if not db.is_file():
            raise HTTPException(503, "Airplay database unavailable")
        days = {"today": 1, "7d": 7, "30d": 30}[period]
        end_day = day or datetime.now(DETROIT).date()
        return {"kind": kind, "period": period, "day": end_day.isoformat(),
                "timezone": "America/Detroit", "station": station,
                "metric": "observed_plays", "coverage": "partial",
                "results": chart(db, kind=kind, day=end_day, days=days, station=station, limit=limit)}

    @app.get("/api/v1/charts/songs")
    def top_songs(station: str | None = None, period: str = Query("today", pattern="^(today|7d|30d)$"),
                  limit: int = Query(20, ge=1, le=100), day: date | None = None) -> dict:
        return get_chart("songs", station, period, limit, day)

    @app.get("/api/v1/charts/artists")
    def top_artists(station: str | None = None, period: str = Query("today", pattern="^(today|7d|30d)$"),
                    limit: int = Query(20, ge=1, le=100), day: date | None = None) -> dict:
        return get_chart("artists", station, period, limit, day)

    return app
