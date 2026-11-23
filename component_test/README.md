# libMusicForge component tests

Run commands from the repository root. Install with
`python -m pip install -e '.[analysis,dev]'` for the analyzer tools.
Run each tool manually and record the platform, inputs and observed output.

| Command | Setup and expected result |
| --- | --- |
| `python component_test/music_analysis_cli.py` | NumPy. Synthetic silence and tones exercise band peaks, onset and calibration. The CLI prints a final PASS after its assertions. |
| `python component_test/wav_music_analysis_cli.py sample.wav` | Uncompressed integer PCM WAV. Check the sample rate and watch the analysis summaries respond to the audio. |
| `python component_test/wav_music_analysis_tui.py sample.wav` | PCM WAV and a curses-capable terminal. Check that the spectrum updates. Optional `--play` also needs FFplay and working audio output. |
| `python examples/mpd_now_playing.py` | Reachable MPD. Play a tagged track and verify artist and title. Stop playback and verify the script reports no track. |
| `python examples/identify_track.py "Collective Soul" "Burn"` | Network access, `MUSICBRAINZ_CONTACT` and `LASTFM_API_KEY`. Check that recording candidates and Last.fm statistics are reported separately. |

CI runs the deterministic suite under `tests/`, using mocked HTTP and synthetic
audio. The live checks cover provider availability, credentials, server setup
and terminal behavior.
