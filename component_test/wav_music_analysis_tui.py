# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Interactive terminal WAV analyzer. No ORC, GUI, or third-party TUI dependencies."""
from __future__ import annotations

import argparse
import curses
import shutil
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
from musicforge.analysis import MusicAnalyzer
from .wav_music_analysis_cli import decode_pcm


def bar(value: float, width: int) -> str:
    count = max(0, min(width, round(value * width)))
    return "#" * count + "." * (width - count)


def run(screen: curses.window, path: Path, fft_size: int, play: bool) -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    screen.keypad(True)
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise ValueError("Only uncompressed integer PCM WAV is supported")
        rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
        if width not in (1, 2, 3, 4) or rate <= 0:
            raise ValueError("Unsupported WAV encoding")
        duration = wav.getnframes() / rate
        analyzer = MusicAnalyzer(fft_size=fft_size, band_count=24)
        player_available = shutil.which("ffplay") is not None
        playback = play and player_available
        status = "Ready"
        frame_index = 0
        start = time.monotonic()
        latest = None

        player_process: subprocess.Popen | None = None

        def player_command(command: str) -> None:
            nonlocal status, player_process
            if not playback:
                return
            if command == "stop":
                if player_process is not None and player_process.poll() is None:
                    player_process.terminate()
                    try:
                        player_process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        player_process.kill()
                        player_process.wait()
                player_process = None
                return
            if command == "play":
                try:
                    player_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error",
                         "-nostats", str(path)],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    status = "FFplay started (timing is approximate)"
                except OSError as exc:
                    status = f"FFplay launch failed: {exc}"

        if playback:
            player_command("play")
        elif play:
            status = "ffplay unavailable; analyzing without sound"
        else:
            status = "Analysis only (use --play for Android audio)"
        try:
            while True:
                key = screen.getch()
                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("r"), ord("R")):
                    if playback:
                        player_command("stop")
                    wav.rewind()
                    analyzer = MusicAnalyzer(fft_size=fft_size, band_count=24)
                    frame_index = 0
                    latest = None
                    start = time.monotonic()
                    if playback:
                        player_command("play")
                elapsed = time.monotonic() - start
                target_index = min(int(elapsed * rate / fft_size), (wav.getnframes() + fft_size - 1) // fft_size)
                # Catch up with playback after slow frames; never show future audio.
                while frame_index < target_index:
                    data = wav.readframes(fft_size)
                    if not data:
                        break
                    pcm = decode_pcm(data, width, channels)
                    if len(pcm) < fft_size:
                        pcm = np.pad(pcm, (0, fft_size - len(pcm)))
                    latest = analyzer.analyze(pcm, rate)
                    frame_index += 1
                audio_time = min(frame_index * fft_size / rate, duration)
                finished = frame_index * fft_size >= wav.getnframes()
                height, columns = screen.getmaxyx()
                screen.erase()

                def line(y: int, value: str) -> None:
                    if 0 <= y < height and columns > 1:
                        try:
                            screen.addnstr(y, 0, value, columns - 1)
                        except curses.error:
                            pass

                line(0, "libMusicForge | WAV Analysis TUI")
                line(1, f"{path.name} | {rate} Hz | {channels} ch | {width * 8} bit")
                line(2, f"{audio_time:6.1f}/{duration:.1f}s | {'FINISHED' if finished else 'RUNNING'} | {'FFPLAY' if playback else 'SILENT'}")
                line(3, "q quit | r restart | --play enables Android media playback")
                line(4, status)
                if latest is not None:
                    width_bar = max(4, min(32, columns - 21))
                    line(6, f"LEVEL  {bar(latest.level, width_bar)} {latest.level:.2f}")
                    line(7, f"BEAT   {bar(latest.beat, width_bar)} {latest.beat:.2f}")
                    for offset, name in enumerate(("bass", "mid", "treble")):
                        value = getattr(latest, name)
                        line(9 + offset, f"{name.upper():6s} {bar(value, width_bar)} {value:.2f}")
                    for offset, name in enumerate(("kick", "snare", "tom_high", "tom_mid", "tom_low", "cymbal")):
                        value = getattr(latest.percussion, name)
                        line(13 + offset, f"{name.upper():8s} {bar(value, width_bar)} {value:.2f}")
                    line(20, "SPECTRUM (low -> high)")
                    # 24 frequency bins as compact vertical bars.
                    spectrum = latest.spectrum
                    usable = min(24, max(0, columns - 2))
                    rows = max(0, min(8, height - 23))
                    for row in range(rows):
                        threshold = (rows - row) / rows
                        line(21 + row, "".join("##" if value >= threshold else "  " for value in spectrum[:usable // 2]) if columns >= 48 else "".join("#" if value >= threshold else " " for value in spectrum[:usable]))
                if height < 22:
                    line(height - 1, "Enlarge terminal for full dashboard")
                screen.refresh()
                time.sleep(0.035)
        finally:
            if playback:
                player_command("stop")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--fft-size", type=int, default=2048)
    parser.add_argument("--play", action="store_true", help="Play WAV using FFplay")
    args = parser.parse_args()
    if not args.wav.is_file():
        parser.error(f"File not found: {args.wav}")
    try:
        curses.wrapper(run, args.wav.resolve(), args.fft_size, args.play)
    except KeyboardInterrupt:
        # Ctrl+C is a normal exit; run() cleans up FFplay in its finally block.
        pass


if __name__ == "__main__":
    main()
