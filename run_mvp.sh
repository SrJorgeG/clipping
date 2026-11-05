#!/usr/bin/env bash
# MVP punta a punta con vídeo sintético (sin streamers, sin YouTube).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="/home/box/bin:${PATH:-}"
PY="${CLIPPING_PYTHON:-/home/box/clipping-venv/bin/python}"
cd "$ROOT"

SAMPLE="$ROOT/samples/demo_peaks.mp4"
if [[ ! -f "$SAMPLE" ]]; then
  echo "[mvp] generando vídeo sintético con picos de volumen…"
  ffmpeg -y -loglevel error \
    -f lavfi -i "sine=frequency=880:sample_rate=44100:duration=20" \
    -f lavfi -i "color=c=0x224466:s=1280x720:d=20:r=30" \
    -filter_complex "[0:a]volume='if(between(t\,4\,6)\,1\,if(between(t\,11\,13)\,1\,0.04))'[a]" \
    -map 1:v -map "[a]" -c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -shortest \
    "$SAMPLE"
fi

echo "[mvp] 1/3 copiar a raw/"
"$PY" "$ROOT/capture/capture.py" --file "$SAMPLE" --name demo_peaks

RAW=$(ls -t "$ROOT/raw"/demo_peaks.* | head -1)
echo "[mvp] raw=$RAW"

echo "[mvp] 2/3 detectar picos"
"$PY" "$ROOT/detect/detect_volume.py" --in "$RAW" --out "$ROOT/candidates/demo_peaks.json" --k-std 1.5 --min-clip 5 --max-clip 10 --pad-before 1.5 --pad-after 2.5 --merge-gap 0.5

echo "[mvp] 3/3 editar cortes"
"$PY" "$ROOT/edit/edit_clips.py" --in "$RAW" --candidates "$ROOT/candidates/demo_peaks.json" --zoom 1.0 --limit 3

echo "[mvp] OK — mira clips/ y queue/queue.json"
ls -la "$ROOT/clips"
echo "--- candidates ---"
"$PY" -c "import json; d=json.load(open('$ROOT/candidates/demo_peaks.json')); print(len(d['candidates']),'candidatos'); [print(c) for c in d['candidates']]"
