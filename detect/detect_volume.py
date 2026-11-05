#!/usr/bin/env python3
"""Detector de picos de volumen (MVP). Emite candidates JSON.

Uso:
  python detect/detect_volume.py --in raw/demo.mp4 --out candidates/demo.json
  python detect/detect_volume.py --in samples/demo.mp4

Fase 2 (stubs): caras (OpenCV Haar), movimiento, Whisper.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def run_ffmpeg_pcm(video: Path, sample_rate: int = 16000) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(video),
        "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-",
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg PCM falló: {r.stderr.decode(errors='replace')[:400]}")
    audio = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if audio.size == 0:
        raise SystemExit("Audio vacío.")
    return audio


def rms_envelope(audio: np.ndarray, sr: int, window_s: float) -> tuple[np.ndarray, np.ndarray]:
    win = max(1, int(sr * window_s))
    n = audio.size // win
    if n == 0:
        raise SystemExit("Vídeo demasiado corto para la ventana.")
    trimmed = audio[: n * win].reshape(n, win)
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-12)
    times = (np.arange(n) + 0.5) * window_s
    return times, rms


def pick_peaks(
    times: np.ndarray,
    rms: np.ndarray,
    method: str,
    k_std: float,
    percentile: float,
    merge_gap: float,
    pad_before: float,
    pad_after: float,
    min_clip: float,
    max_clip: float,
    duration: float,
) -> list[dict]:
    if method == "percentile":
        thr = float(np.percentile(rms, percentile))
    else:
        thr = float(np.median(rms) + k_std * rms.std())

    median = float(np.median(rms)) + 1e-9
    above = rms >= thr
    candidates: list[dict] = []
    i = 0
    n = len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        seg_t = times[i:j]
        seg_r = rms[i:j]
        peak_idx = int(np.argmax(seg_r))
        peak_t = float(seg_t[peak_idx])
        # ignorar transitorios al inicio del fichero
        if peak_t < 0.35:
            i = j
            continue
        peak_score = float(seg_r[peak_idx] / median)
        start = max(0.0, peak_t - pad_before)
        end = min(duration, peak_t + pad_after)
        if end - start < min_clip:
            end = min(duration, start + min_clip)
        if end - start > max_clip:
            end = start + max_clip
        candidates.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "peak": round(peak_t, 3),
            "score": round(peak_score, 4),
            "reason": "volume_peak",
            "threshold": round(thr, 6),
        })
        i = j

    if not candidates:
        return []
    candidates.sort(key=lambda c: c["start"])
    merged: list[dict] = [candidates[0]]
    for c in candidates[1:]:
        prev = merged[-1]
        if c["start"] <= prev["end"] + merge_gap:
            if c["score"] > prev["score"]:
                prev["peak"] = c["peak"]
                prev["score"] = c["score"]
                # recentrar ventana en el pico fuerte
                start = max(0.0, prev["peak"] - pad_before)
                end = min(duration, prev["peak"] + pad_after)
                if end - start < min_clip:
                    end = min(duration, start + min_clip)
                if end - start > max_clip:
                    end = start + max_clip
                prev["start"] = round(start, 3)
                prev["end"] = round(end, 3)
            else:
                prev["end"] = round(min(duration, max(prev["end"], c["end"])), 3)
                if prev["end"] - prev["start"] > max_clip:
                    prev["end"] = round(prev["start"] + max_clip, 3)
        else:
            merged.append(c)
    return merged



def stub_faces(_video: Path) -> list[dict]:
    """Fase 2: OpenCV Haar / MediaPipe. Stub vacío."""
    return []


def stub_motion(_video: Path) -> list[dict]:
    """Fase 2: frame differencing. Stub vacío."""
    return []


def probe_duration(video: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffprobe falló: {r.stderr[:300]}")
    return float(r.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description="Detector de picos de volumen → JSON")
    ap.add_argument("--in", dest="inp", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--window", type=float, default=0.25)
    ap.add_argument("--method", choices=("std", "percentile"), default="std")
    ap.add_argument("--k-std", type=float, default=1.8)
    ap.add_argument("--percentile", type=float, default=92)
    ap.add_argument("--pad-before", type=float, default=1.0)
    ap.add_argument("--pad-after", type=float, default=2.5)
    ap.add_argument("--min-clip", type=float, default=8.0)
    ap.add_argument("--max-clip", type=float, default=35.0)
    ap.add_argument("--merge-gap", type=float, default=2.0)
    ap.add_argument("--faces", action="store_true", help="Fase 2 stub")
    ap.add_argument("--motion", action="store_true", help="Fase 2 stub")
    args = ap.parse_args()

    video = args.inp.expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"No existe: {video}")

    out = args.out
    if out is None:
        out = ROOT / "candidates" / f"{video.stem}.json"
    out = out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    sr = 16000
    print(f"[detect] PCM {video.name} …", flush=True)
    audio = run_ffmpeg_pcm(video, sr)
    duration = probe_duration(video)
    times, rms = rms_envelope(audio, sr, args.window)
    peaks = pick_peaks(
        times, rms, args.method, args.k_std, args.percentile,
        args.merge_gap, args.pad_before, args.pad_after,
        args.min_clip, args.max_clip, duration,
    )

    extras = []
    if args.faces:
        extras.extend(stub_faces(video))
    if args.motion:
        extras.extend(stub_motion(video))

    payload = {
        "source": str(video),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration": round(duration, 3),
        "params": {
            "window": args.window,
            "method": args.method,
            "k_std": args.k_std,
            "percentile": args.percentile,
        },
        "candidates": peaks,
        "stubs": {"faces": extras if args.faces else "disabled", "motion": "disabled" if not args.motion else extras},
        "phase2": ["faces_haar_or_mediapipe", "motion_frame_diff", "whisper_keywords"],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[detect] {len(peaks)} candidatos → {out}", flush=True)
    for c in peaks:
        print(f"  {c['start']:.2f}-{c['end']:.2f}s  score={c['score']:.2f}  peak@{c['peak']:.2f}s")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
