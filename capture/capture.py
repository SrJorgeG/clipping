#!/usr/bin/env python3
"""Captura stream (Streamlink/yt-dlp) o copia un fichero local a raw/.

No publica nada. Uso:
  python capture/capture.py --file samples/demo.mp4
  python capture/capture.py --url 'https://www.twitch.tv/CHANNEL' --duration 60
  python capture/capture.py --url 'https://www.youtube.com/watch?v=ID' --backend ytdlp --duration 60
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def resolve_tools() -> dict[str, str]:
    # Prefer venv CLIs if PATH has /home/box/bin
    tools = {}
    for name in ("streamlink", "yt-dlp", "ffmpeg"):
        p = which(name)
        if not p and name != "ffmpeg":
            candidate = Path("/home/box/clipping-venv/bin") / name
            if candidate.exists():
                p = str(candidate)
        if not p and name == "ffmpeg":
            p = which("ffmpeg")
        if not p:
            raise SystemExit(f"Falta {name}. Activa PATH=/home/box/bin:$PATH o instala el binario.")
        tools[name] = p
    return tools


def copy_file(src: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    # store FS may block utime/copystat — copy bytes only
    out.write_bytes(src.read_bytes())
    return out


def capture_streamlink(url: str, out: Path, quality: str, duration: int, streamlink: str, ffmpeg: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Streamlink → stdout → ffmpeg con -t si duration > 0
    sl_cmd = [streamlink, url, quality, "-O", "--retry-streams", "3"]
    ff_cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", "pipe:0"]
    if duration and duration > 0:
        ff_cmd += ["-t", str(duration)]
    ff_cmd += ["-c", "copy", str(out)]
    print(f"[capture] streamlink → {out.name} (duration={duration or 'live'})", flush=True)
    sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert sl.stdout is not None
    ff = subprocess.Popen(ff_cmd, stdin=sl.stdout, stderr=subprocess.PIPE)
    sl.stdout.close()
    _, ff_err = ff.communicate()
    sl.wait(timeout=30)
    if ff.returncode != 0:
        raise SystemExit(f"ffmpeg falló: {ff_err.decode(errors='replace')[:500]}")
    if not out.exists() or out.stat().st_size < 1024:
        sl_err = sl.stderr.read().decode(errors="replace") if sl.stderr else ""
        raise SystemExit(f"Captura vacía. streamlink stderr:\n{sl_err[:800]}")
    return out


def capture_ytdlp(url: str, out: Path, duration: int, ytdlp: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    # yt-dlp escribe su propio nombre; forzamos salida
    tmp_tmpl = str(out.with_suffix("")) + ".%(ext)s"
    cmd = [ytdlp, "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", tmp_tmpl]
    if duration and duration > 0:
        # descarga live segment aproximadamente
        cmd += ["--download-sections", f"*0-{duration}"]
    cmd.append(url)
    print(f"[capture] yt-dlp → {out.name}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"yt-dlp falló:\n{r.stderr[:800]}")
    # encontrar fichero generado
    candidates = list(out.parent.glob(out.stem + ".*"))
    candidates = [c for c in candidates if c.suffix.lower() in {".mp4", ".mkv", ".webm"}]
    if not candidates:
        raise SystemExit("yt-dlp no produjo vídeo.")
    produced = max(candidates, key=lambda p: p.stat().st_mtime)
    if produced != out:
        produced.replace(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Captura a raw/ (Streamlink, yt-dlp o fichero local)")
    ap.add_argument("--url", help="URL Twitch/YouTube/Kick live o VOD")
    ap.add_argument("--file", type=Path, help="Vídeo local de prueba a copiar a raw/")
    ap.add_argument("--backend", choices=("streamlink", "ytdlp", "file"), default=None)
    ap.add_argument("--quality", default="best")
    ap.add_argument("--duration", type=int, default=60, help="Segundos a grabar (live). 0 = sin límite.")
    ap.add_argument("--name", default=None, help="Nombre base del fichero de salida")
    args = ap.parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")
    name = args.name or f"capture_{ts}"
    out = RAW / f"{name}.mp4"

    if args.file:
        src = args.file.expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"No existe: {src}")
        dest = RAW / f"{name}{src.suffix or '.mp4'}"
        copy_file(src, dest)
        print(dest)
        return 0

    if not args.url:
        raise SystemExit("Pasa --file o --url")

    tools = resolve_tools()
    backend = args.backend or "streamlink"
    if backend == "streamlink":
        path = capture_streamlink(args.url, out, args.quality, args.duration, tools["streamlink"], tools["ffmpeg"])
    elif backend == "ytdlp":
        path = capture_ytdlp(args.url, out, args.duration, tools["yt-dlp"])
    else:
        raise SystemExit("backend file requiere --file")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
