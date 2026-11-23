# libMusicForge examples

Run these scripts from the repository root after installing the library
with `python -m pip install -e .`.

| Example | Use it to |
| --- | --- |
| [compare_tracks.py](compare_tracks.py) | Compare listener counts and scrobbles for multiple artist/title pairs using `LASTFM_API_KEY`. |
| [identify_track.py](identify_track.py) | Look up MusicBrainz candidates and Last.fm statistics using `MUSICBRAINZ_CONTACT` and `LASTFM_API_KEY`. |
| [resolve_track.py](resolve_track.py) | Resolve manually supplied player metadata against MusicBrainz using `MUSICBRAINZ_CONTACT`. |
| [mpd_now_playing.py](mpd_now_playing.py) | Read the current track from a reachable MPD server. |

The [README](../README.md#lastfm-statistics) has a direct single-track Last.fm
API example. For PCM and live service verification, see the
[component test guide](../component_test/README.md).
