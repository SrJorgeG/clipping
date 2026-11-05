#!/usr/bin/env python3
"""Editor MVP: corta candidatos con ffmpeg (estilo CapCut ligero).

- Aspecto 9:16 (crop centro) o 16:9
- Zoom ligero opcional
- SRT placeholder por clip
- Copia a clips/ y opcionalmente encola en queue/ (NUNCA sube)

Uso:
  python edit/edit_clips.py --in raw/demo.mp4 --candidates candidates/demo.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ROOT / "clips"
READY = ROOT / "ready_to_upload"
QUEUE = ROOT / "queue" / "queue.json"


def cut_clip(
    video: Path,
    start: float,
    end: float,
    out: Path,
    aspect: str,
    width: int,
    height: int,
    zoom: float,
    fade_in: float,
    fade_out: float,
) -> None:
    dur = max(0.1, end - start)
    vf_parts = []
    if aspect == "9:16":
        # scale then crop center to 9:16
        vf_parts.append(
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
    else:
        vf_parts.append(f"scale={width}:-2")
    if zoom and zoom > 1.001:
        # zoompan suave sobre la duración del clip
        z = zoom
        vf_parts.append(
            f"zoompan=z='min({z},1+0.001*on)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=30"
        )
    if fade_in > 0:
        vf_parts.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out > 0 and dur > fade_out:
        vf_parts.append(f"fade=t=out:st={max(0, dur - fade_out)}:d={fade_out}")
    vf = ",".join(vf_parts) if vf_parts else "null"
    af = []
    if fade_in > 0:
        af.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0 and dur > fade_out:
        af.append(f"afade=t=out:st={max(0, dur - fade_out)}:d={fade_out}")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-i", str(video),
        "-vf", vf,
    ]
    if af:
        cmd += ["-af", ",".join(af)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # fallback sin zoompan (a veces falla en clips cortos)
        cmd_simple = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-i", str(video),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", str(out),
        ]
        r2 = subprocess.run(cmd_simple, capture_output=True, text=True)
        if r2.returncode != 0:
            raise SystemExit(f"ffmpeg corte falló:\n{r.stderr[:400]}\n{r2.stderr[:400]}")


def write_srt(path: Path, start: float, end: float, text: str) -> None:
    # SRT relativo al clip (empieza en 0)
    dur = end - start
    def ts(s: float) -> str:
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = int(s % 60)
        ms = int((s - int(s)) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    body = f"1\n{ts(0)} --> {ts(max(0.5, dur - 0.1))}\n{text}\n"
    path.write_text(body, encoding="utf-8")


def enqueue(item: dict) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    data = {"items": [], "updated_at": None}
    if QUEUE.exists():
        try:
            data = json.loads(QUEUE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data.setdefault("items", []).append(item)
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    data["note"] = "Cola local. NUNCA sube a YouTube ni a ningún sitio sin petición explícita de Jorge."
    QUEUE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Corta clips desde candidates JSON")
    ap.add_argument("--in", dest="inp", required=True, type=Path)
    ap.add_argument("--candidates", required=True, type=Path)
    ap.add_argument("--aspect", default="9:16", choices=("9:16", "16:9"))
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--zoom", type=float, default=1.0, help="1.0 = sin zoom; 1.08 ligero")
    ap.add_argument("--limit", type=int, default=5, help="Máx clips a generar")
    ap.add_argument("--no-queue", action="store_true")
    ap.add_argument("--ready", action="store_true", help="También copia a ready_to_upload/")
    args = ap.parse_args()

    video = args.inp.expanduser().resolve()
    cand_path = args.candidates.expanduser().resolve()
    payload = json.loads(cand_path.read_text(encoding="utf-8"))
    cands = payload.get("candidates") or []
    if not cands:
        print("[edit] sin candidatos; nada que cortar")
        return 0

    CLIPS.mkdir(parents=True, exist_ok=True)
    if args.ready:
        READY.mkdir(parents=True, exist_ok=True)

    w, h = args.width, args.height
    if args.aspect == "16:9":
        w, h = 1920, 1080

    made = []
    for i, c in enumerate(cands[: args.limit]):
        start, end = float(c["start"]), float(c["end"])
        out = CLIPS / f"{video.stem}_clip{i:02d}_{start:.0f}-{end:.0f}.mp4"
        print(f"[edit] {start:.2f}-{end:.2f} → {out.name}", flush=True)
        cut_clip(video, start, end, out, args.aspect, w, h, args.zoom, 0.12, 0.18)
        srt = out.with_suffix(".srt")
        write_srt(srt, start, end, f"[placeholder] momento {i+1} · score {c.get('score', '?')}")
        item = {
            "id": f"{video.stem}_{i:02d}",
            "source": str(video),
            "clip": str(out),
            "srt": str(srt),
            "start": start,
            "end": end,
            "score": c.get("score"),
            "reason": c.get("reason"),
            "status": "ready_local",
            "upload": False,
        }
        if args.ready:
            dest = READY / out.name
            dest.write_bytes(out.read_bytes())
            item["ready_to_upload"] = str(dest)
        if not args.no_queue:
            enqueue(item)
        made.append(out)

    print(f"[edit] {len(made)} clips en {CLIPS}")
    for p in made:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
