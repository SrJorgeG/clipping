# N8N — orquestación (cuatro workflows)

Alineado con la Page canónica «Clipping automatizado — setup GTA 6».

El box **no tiene Docker** ahora mismo. Opciones para Jorge:

## Opción A — Docker (recomendada en jorge-cachy / VPS)

```bash
docker volume create n8n_data
docker run -d --name n8n --restart unless-stopped \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -v /ruta/al/clipping:/data/clipping \
  docker.n8n.io/n8nio/n8n
```

Abre http://localhost:5678

## Opción B — npx (rápido, sin Docker)

```bash
npx n8n
```

Requiere Node 20 (el box ya lo tiene). Datos en `~/.n8n`.

## Workflows (A→D)

| ID | Nombre | Trigger | Acción |
|----|--------|---------|--------|
| A | Ingestión | Schedule / Webhook OBS | `capture/capture.py` → `raw/` |
| B | Detección | archivo nuevo en `raw/` | `detect/detect_volume.py` → `candidates/` |
| C | Edición | candidates con score | `edit/edit_clips.py` → `clips/` + cola |
| D | Publicación | **APARCADO** | YouTube API — solo cuando Jorge lo pida |

Importa `workflows_skeleton.json` (esqueleto; nodos Execute Command apuntan a rutas del proyecto).
**Workflow D no sube nada** en este esqueleto: solo un sticky note de bloqueo.
