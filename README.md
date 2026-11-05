# Pipeline de clipping (setup)

Proyecto del bot **Clipping** (Jorge Gómez De Oliveira, Madrid).

Plan canónico (Page): [Clipping automatizado — setup GTA 6](https://cursor.com/canvas/store-9b2f9f3c-53d9-441b-977c-f9e4b2a3e1a7/d16139d9-7195-414f-a69c-3c88e8ed34cf)

**Regla:** no se publica ni sube nada a YouTube (ni a ningún sitio) sin petición explícita de Jorge. La cola es solo local.

## Objetivo

`captura → detector (volumen MVP) → editor 9:16 → cola local`  
N8N orquesta cuatro workflows (A–D). D está bloqueado a propósito.

Prueba el MVP con **vídeo local sintético** (o cualquier MP4/VOD). No depende de GTA 6 ni de buscar streamers.

## Dónde vive

| Qué | Ruta |
|-----|------|
| Proyecto | `/cursor/stores/store-6c93636b-b600-42da-acf0-0b8212f9490a/clipping` |
| Venv Python (streamlink, yt-dlp, opencv, pyyaml) | `/home/box/clipping-venv` |
| CLIs en PATH | `/home/box/bin` → `streamlink`, `yt-dlp`, `clipping-python` |

El store no permite symlinks de venv; por eso el entorno está en disco del box.

## Estructura

```
clipping/
  capture/capture.py      # Streamlink / yt-dlp / fichero → raw/
  detect/detect_volume.py # picos de volumen → candidates/*.json
  detect/faces_motion_stub.py  # fase 2
  edit/edit_clips.py      # cortes ffmpeg 9:16 → clips/ + queue/
  queue/queue.json         # cola local (sin upload)
  n8n/                    # instrucciones + esqueleto A–D
  samples/                # vídeo de prueba
  raw/ clips/ candidates/ ready_to_upload/ archive/ out/
  config.example.yaml
  run_mvp.sh
```

## Instalado en el box (5 nov 2026)

- ffmpeg 7.1 (sistema)
- Node 20 / npx (sistema) — para `npx n8n` si hace falta
- streamlink 8.6.3 (venv)
- yt-dlp 2026.10.26 (venv)
- opencv-python-headless 5.0 (venv) — listo para fase 2
- numpy, pyyaml (venv)

**Falta / blockers**

- Docker (no hay socket ni demonio) → N8N vía `npx n8n` o Docker en `jorge-cachy` / portátil
- Whisper / faster-whisper (fase 2; no instalado a propósito)
- torch grande (no)
- YouTube OAuth (no; a propósito)

## Probar el MVP (un comando)

```bash
export PATH="/home/box/bin:$PATH"
bash /cursor/stores/store-6c93636b-b600-42da-acf0-0b8212f9490a/clipping/run_mvp.sh
```

Genera un MP4 sintético con 2 picos de audio, detecta timestamps y corta clips a `clips/`.

### Pasos manuales

```bash
export PATH="/home/box/bin:$PATH"
PY=/home/box/clipping-venv/bin/python
ROOT=/cursor/stores/store-6c93636b-b600-42da-acf0-0b8212f9490a/clipping
cd "$ROOT"

# 1) Captura desde fichero local (o --url con streamlink)
$PY capture/capture.py --file samples/demo_peaks.mp4 --name demo

# 2) Detectar
$PY detect/detect_volume.py --in raw/demo.mp4 --out candidates/demo.json

# 3) Editar (sin subir)
$PY edit/edit_clips.py --in raw/demo.mp4 --candidates candidates/demo.json
```

Streamlink genérico (cuando haya un live con permiso):

```bash
$PY capture/capture.py --url 'https://www.twitch.tv/CANAL' --duration 90 --name live_test
```

## N8N

Ver `n8n/README.md`. Cuatro workflows: A ingestión, B detección, C edición, D publicación bloqueada.

## Decisiones pendientes (Jorge)

1. ¿Captura principal en el **box (Streamlink)** o **OBS en jorge-cachy / jorge-portatil**?
2. ¿Dónde corre **N8N**: box con `npx n8n`, Docker en cachy, o N8N Cloud?
3. ¿Idioma de subtítulos por defecto: **es-ES**, en-US, o bilingüe?
4. ¿Canal de YouTube de destino (solo nombre; OAuth más adelante, cuando diga él)?

## Fase 2 (después del MVP)

- Caras: OpenCV Haar / MediaPipe
- Movimiento: frame differencing
- Whisper → SRT karaoke
- Plantillas YAML CapCut-like más ricas
- Workflow D solo con luz verde explícita

## Repositorio

Código y docs: https://github.com/SrJorgeG/clipping
