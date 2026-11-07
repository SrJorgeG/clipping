# Decisión propuesta (pendiente): OpenShorts en el pipeline

**Estado:** PROPUESTA. No aprobada y no implementada. Informe: [../openshorts-research-2026-11-07.md](../openshorts-research-2026-11-07.md)

## Propuesta
| Etapa actual | Propuesta | Motivo |
|---|---|---|
| A: captura con Streamlink/yt-dlp (+OBS) | **Conservar** | OpenShorts no graba directos en curso; trabaja con VOD/URL/fichero |
| B: detección por volumen con ffmpeg | **Sustituir (a prueba)** | Ventanas sobre la transcripción y corte ajustado al borde de palabra |
| Cortes de plano / YuNet pendiente | **Sustituir (a prueba)** | TransNetV2 y MediaPipe/YOLOv8 (TRACK/GENERAL/SCREENCAST) |
| C: crop 9:16 fijo + subtítulos placeholder | **Sustituir (a prueba)** | Reencuadre dinámico y subtítulos quemados con FFmpeg |
| n8n + runner :8787 | **Complementar** | n8n llama a `POST /api/process` (:8000); el webhook de vuelta rechaza IPs privadas, así que hay que leer `./output` |
| D: orquestador sin publicar | **Conservar la restricción** | No usar el workflow `content-machine` (publica con `/api/social/post`) |

## Condiciones antes de decidir
1. Prueba reversible con un único vídeo en español con permiso, sin subir nada, primero en CPU. Ver la sección «Prueba reversible» del informe.
2. Medir nosotros: frases completas (el código solo garantiza borde de palabra), calidad de la transcripción ES (por defecto el idioma se autodetecta con `small`), encuadre, subtítulos y tiempo en CPU/GPU (la 2060 tiene 6 GB; el proyecto solo declara suficientes 8 GB).
3. Resolver dependencias: Gemini (`GEMINI_API_KEY`) o un LLM local (`LLM_BASE_URL`); licencia AGPL de los pesos YOLOv8n si hay uso comercial; no hay releases a los que fijar versión.
4. Permiso explícito de cada streamer antes de clipear o monetizar.
