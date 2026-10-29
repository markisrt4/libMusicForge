# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Analyze a PCM WAV file using libMusicForge, without ORC or audio hardware.

Supports uncompressed 8/16/24/32-bit integer PCM WAV. Downmixes channels to mono.
"""
from __future__ import annotations

import argparse
import time
import wave
from pathlib import Path

import numpy as np

from musicforge.analysis import MusicAnalyzer


def decode_pcm(data: bytes, width: int, channels: int) -> np.ndarray:
    if width == 1:
        samples = (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        octets = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = octets[:, 0] | (octets[:, 1] << 8) | (octets[:, 2] << 16)
        values = (values ^ 0x800000) - 0x800000
        samples = values.astype(np.float32) / 8388608.0
    elif width == 4:
        samples = np.frombuffer(data, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported PCM sample width: {width} bytes")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples


def analyze_wav(path: Path, fft_size: int, interval: float) -> None:
    analyzer = MusicAnalyzer(fft_size=fft_size, band_count=24)
    started = time.perf_counter()
    peak_level = 0.0
    max_beat = 0.0
    beat_onsets = 0
    previous_beat = 0.0
    frames = 0
    totals = {key: 0.0 for key in ("bass", "mid", "treble", "kick", "snare", "cymbal")}
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise ValueError("Compressed WAV is unsupported; convert to integer PCM WAV")
        rate, channels, width, count = wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()
        if rate <= 0 or channels <= 0:
            raise ValueError("Invalid WAV format")
        duration = count / rate
        print(f"File: {path}")
        print(f"Format: {rate} Hz, {channels} channel(s), {width * 8}-bit PCM, {duration:.2f} s")
        print(f"Analysis: FFT={fft_size}, block={fft_size / rate * 1000:.1f} ms")
        next_report = interval
        while True:
            chunk = wav.readframes(fft_size)
            if not chunk:
                break
            samples = decode_pcm(chunk, width, channels)
            if samples.size < fft_size:
                samples = np.pad(samples, (0, fft_size - samples.size))
            state = analyzer.analyze(samples, rate)
            frames += 1
            peak_level = max(peak_level, state.level)
            max_beat = max(max_beat, state.beat)
            if state.beat > 0.35 and (previous_beat <= 0.35 or state.beat > previous_beat * 1.6):
                beat_onsets += 1
            previous_beat = state.beat
            for key in ("bass", "mid", "treble"):
                totals[key] += getattr(state, key)
            for key in ("kick", "snare", "cymbal"):
                totals[key] += getattr(state.percussion, key)
            elapsed_audio = min(frames * fft_size / rate, duration)
            if interval > 0 and elapsed_audio >= next_report:
                dominant = max(("bass", "mid", "treble"), key=lambda key: getattr(state, key))
                print(f"{elapsed_audio:7.2f}s level={state.level:.2f} beat={state.beat:.2f} "
                      f"kick={state.percussion.kick:.2f} snare={state.percussion.snare:.2f} "
                      f"cymbal={state.percussion.cymbal:.2f} dominant={dominant}")
                next_report += interval
    if not frames:
        raise ValueError("WAV contains no audio frames")
    processing = time.perf_counter() - started
    print("\nSummary")
    print(f"Blocks: {frames}, peak level: {peak_level:.3f}, peak beat: {max_beat:.3f}")
    print(f"Beat candidates (heuristic, NOT BPM): {beat_onsets}")
    print("Mean normalized activity: " + ", ".join(f"{key}={value / frames:.3f}" for key, value in totals.items()))
    print(f"Processing time: {processing:.3f}s, throughput: {duration / max(processing, 1e-9):.1f}x realtime")
    print("PASS: WAV processed with libMusicForge")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path, help="Path to an uncompressed integer PCM WAV file")
    parser.add_argument("--fft-size", type=int, default=2048, help="FFT samples per analysis block (default: 2048)")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between progress reports (0 disables)")
    args = parser.parse_args()
    if not args.wav.is_file():
        parser.error(f"WAV file not found: {args.wav}")
    if args.interval < 0:
        parser.error("--interval must be >= 0")
    analyze_wav(args.wav, args.fft_size, args.interval)


if __name__ == "__main__":
    main()
