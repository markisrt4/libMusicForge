"""Launch the read-only MusicForge airplay API.

MUSICFORGE_AIRPLAY_DB=/path/to/airplay.sqlite3 uvicorn examples.serve_airplay_api:app --host 127.0.0.1 --port 8000
"""
import os

from musicforge.airplay.api import create_app

app = create_app(os.environ.get("MUSICFORGE_AIRPLAY_DB", "airplay.sqlite3"))
