# Investigación: OpenShorts como sustituto parcial del pipeline de clipping

- **Fecha:** 2026-11-07
- **Estado:** investigación documental. **No se ha migrado, instalado ni probado OpenShorts.** El stack actual (runner :8787, n8n, cloudflared) sigue igual y parado.
- **Método:** workflow `/deep-research` del Grok CLI (v1.0.77) lanzado en jorge-cachy en modo headless, con permisos por defecto. Resultado **parcial**: 6 preguntas, 10 agentes, 22 de 24 afirmaciones verificadas y 12 candidatas descartadas por el tope del workflow. Después se hizo una comprobación mínima con la API de GitHub y el README oficial: licencia MIT, fork de `kamilstanuch/Autocrop-vertical`, HEAD `8fa411f` del 2026-11-07 00:20 (Madrid) y requisito «Docker, 8GB+ RAM».
- **Proyecto:** https://github.com/mutonby/openshorts · https://www.openshorts.app/ (no confundir con OpenShot, el editor de vídeo).

> Distinción importante: lo que pone «el código hace X» se ha leído en el código fuente. Los tiempos de proceso (5–8 min en CPU, ~50 s en GPU) y los precios salen de la web o del README del proyecto. **No son mediciones propias** y no se han comprobado.

Decisión propuesta: [decisions/2026-11-07-openshorts.md](decisions/2026-11-07-openshorts.md)

## Resumen


OpenShorts es un generador de clips con IA, de código abierto, que convierte vídeos largos en clips verticales 9:16. El sitio oficial es https://www.openshorts.app/ y el código para autoalojarlo es https://github.com/mutonby/openshorts; no es OpenShot, el editor de vídeo de escritorio de Jonathan Thomas (Python/PyQt5 y libopenshot), bajo GPL-3.0 o posterior. [S1][S2] No captura un directo en curso: solo entra un VOD, un enlace que baje yt-dlp o un fichero, y un livestream ya terminado se trata como VOD largo con la descarga acotada por minutos, no como una grabación continua, así que Streamlink y OBS se conservan. [S17][S19] El núcleo (todo menos cloud/) es MIT y permite uso comercial, incluida la venta de copias; cloud/ solo autoriza uso personal o interno y prohíbe ofrecerlo a terceros como servicio alojado o de pago sin acuerdo escrito, y autoalojar el núcleo no exige esa carpeta. [S4] Puede sustituir la detección por volumen y el montaje 9:16 del MVP y dejarse disparar desde n8n, pero el corte a frase completa no está demostrado, el español no está forzado ni enseñado en una demo, no hay dato sobre una GTX/RTX 2060 de 6 GB, y los tiempos publicados no son una medición citable. [S13][S14][S11][S18]

### Identidad, homónimos y mantenimiento

El repositorio que enlaza el sitio sigue siendo un fork de kamilstanuch/Autocrop-vertical (padre no archivado, último push el 2026-02-15). agusmakmun/openshorts es un fork de mutonby, no la fuente. jnMetaCode/openshorts es otro proyecto, sin fork, con homepage https://os.aiolaola.com, descrito como el pipeline local «OpenShorts (Kaipian)». [S3]

A 7 de noviembre de 2026 el HEAD de main es 8fa411fed239247713012069dd170a5431ebe911 (2026-11-06T23:20:41Z, victorcavero14). No hay releases ni tags. El repo no está archivado: 7542 estrellas, 1632 forks, 5 issues abiertos y 46 cerrados. En contribuidores constan victorcavero14 (98), mutonby (8) y kamilstanuch (6). [S5]

### Modelos, claves y hardware

La imagen descarga yolov8n.pt mediante Ultralytics; los modelos YOLOv8 se publican bajo AGPL-3.0 o licencia Enterprise. El repo fija faster-whisper 1.2.1 (código y pesos de Whisper en MIT) y MediaPipe 0.10.14 (Apache-2.0), e invoca Gemini, ElevenLabs y fal.ai como APIs que aporta quien lo despliega. [S6]

Por defecto la transcripción es faster-whisper small, en CPU y int8. Parakeet (nemo-parakeet-tdt-0.6b-v3) solo entra si TRANSCRIBE_BACKEND=parakeet. Las escenas usan TransNetV2 y, si falla, PySceneDetect ContentDetector. El seguimiento carga yolov8n.pt y MediaPipe FaceDetection con model_selection=1. El selector de momentos usa GEMINI_MODEL o, si no está, gemini-3.1-flash-lite. [S9]

Sin LLM_BASE_URL, el recorte de un vídeo con habla se aborta si falta GEMINI_API_KEY. Un LLM local solo sustituye a Gemini al elegir momentos; un vídeo sin habla sigue pidiendo Gemini, porque un modelo de solo texto no ve la imagen. ElevenLabs (doblaje), fal.ai (AI Shorts) y Upload-Post (publicación) no forman parte de ese paso. Con LLM_BASE_URL la clave de Gemini deja de pedirse en el panel salvo para el layout y los vídeos mudos. Las fuentes no dan precios. [S10]

La imagen por defecto es solo CPU. El README afirma que 8 GB de VRAM bastan para large-v3-turbo en fp16 más los modelos de detección, y ante un error CUDA de Whisper el código reintenta una vez en CPU con int8. GPU_MIN_FREE_MB vale 4500 por defecto, pero si no hay trabajos en curso la admisión deja pasar. Ninguna de esas piezas documenta que una GTX/RTX 2060 de 6 GB en CachyOS, con unos 300 GB de disco, deba ir en CPU o quepa en GPU. [S11]

### Arquitectura y n8n

docker-compose define tres servicios: backend FastAPI en 8000:8000 (contenedor openshorts-backend, volumen ./output:/app/output), frontend Vite en 5175:5173 y renderer Remotion en 3100:3100 con OUTPUT_DIR=/output. El empaquetado expone el puerto 8000 con uvicorn; torch de GPU solo si se construye con GPU=1. [S7]

La cola es interna al proceso (asyncio.PriorityQueue y un semáforo, 5 trabajos concurrentes por defecto), no un broker. POST /api/process acepta webhook_url y webhook_secret opcionales, firma el cuerpo con HMAC-SHA256 y llama a una comprobación de URL pública al encolar y en cada entrega: rechaza loopback, direcciones privadas, link-local y 100.64.0.0/10, y responde HTTP 400 si la URL no vale. Un n8n en Docker, en localhost o en red privada, puede lanzar el trabajo contra http://localhost:8000, pero no puede ser el destino de ese callback. [S8]

El workflow de ejemplo openshorts-clip-and-notify recibe los clips por webhook firmado y no publica. En autoalojado la base es http://localhost:8000 sin clave de API. El MCP local es http://localhost:8000/mcp o python mcp_stdio.py, y el CLI usa OPENSHORTS_API_URL=http://localhost:8000, también sin clave. Otro workflow del repo (content-machine) sí hace POST /api/social/post. [S12]

### Qué hace el código frente a lo que afirma la web

El snap del clip exportado cae en el borde de la palabra, más un margen de silencio, para no cortar a media palabra. El prompt de detalle pide no cortar a media palabra o frase. Alinear las ventanas de puntuación a segmentos de Whisper evita partir una frase dentro de la ventana, y eso no es el corte del clip. La web atribuye los bordes a timestamps de palabra y a no empezar a mitad de plano, no a un límite de oración. [S13]

Hay timestamps por palabra y el contrato admite un código corto de idioma, incluido «es». El modelo por defecto es small, no se pasa language= (se guarda el idioma autodetectado) y no hay una demo pública de transcripción en español. Parakeet lista «es» entre 25 idiomas, pero es un backend opcional de GPU. [S14]

El 9:16 está implementado: TRACK (caras de MediaPipe, con fallback de persona en YOLOv8n) y GENERAL (fondo desenfocado). Pantalla, gameplay a cuadro entero y facecam de esquina van por SCREENCAST, WIDE e INSET; SCREENCAST sale apagado por defecto. Encaja con lo que la web describe para gameplay y facecam. [S15] Los subtítulos del clip se queman con FFmpeg (filtro ass o subtitles y reencode), no son un overlay de la interfaz. [S16]

Los tiempos de unos 5–8 minutos en CPU y unos 50 segundos, o cerca de un minuto, en GPU NVIDIA para un vídeo de 8 minutos —con una RTX 4060 citada solo como ejemplo de tarjeta con NVENC— están en la web y en el README. No hay registro de medición ni de hardware que se pueda citar. [S18]

### Matriz frente al pipeline actual

La captura del directo y el orquestador que no publica se quedan; el criterio de volumen, el crop fijo y el subtítulo de relleno son lo que este código puede ocupar; n8n solo complementa, por HTTP de entrada y por ficheros de salida.

| Etapa | Decisión | Justificación |
|---|---|---|
| Adquisición Streamlink/yt-dlp (OBS opcional) | **Conservar** | No hay enganche a un directo en curso ni grabación continua; un livestream acabado entra como VOD recortado por minutos. [S17][S19] |
| Detección por volumen con ffmpeg | **Sustituir** | Los candidatos salen de ventanas alineadas a segmentos de la transcripción y el corte exportado se encaja al inicio y al final de palabra y a la pausa de alrededor, no a un umbral de audio. [S20] |
| Cortes de plano | **Sustituir** | El motor por defecto es TransNetV2; PySceneDetect ContentDetector solo actúa si TransNetV2 falla o se pide el motor legado. No es el detector de volumen del MVP. [S21] |
| YuNet pendiente y crop 9:16 fijo con ffmpeg | **Sustituir** | Por escena se elige TRACK o GENERAL según el recuento de caras de MediaPipe, con YOLOv8 como respaldo de persona. requirements.txt fija MediaPipe y Ultralytics y no lista YuNet. [S22][S15] |
| Subtítulos placeholder (faster-whisper ya instalado) | **Sustituir el quemado** | El exportado lleva los subtítulos incrustados por FFmpeg a partir del transcript con palabras. [S16] |
| n8n en Docker y runner :8787 (/capture, /detect, /edit) | **Complementar** | /capture sigue fuera. Detección y edición pueden delegarse en POST al puerto 8000, sin clave en autoalojado, leyendo ./output. El webhook de vuelta no acepta la IP privada de ese n8n. [S8][S12] |
| Workflow D (orquestador, sin publicar) | **Conservar esa restricción** | El ejemplo clip-and-notify no publica; el content-machine sí llama a POST /api/social/post y no debe usarse en la prueba. [S12] |

### Prueba reversible

Dejar el workflow A como está y no retirar el runner de :8787 hasta comparar. Cuando el fichero ya esté cerrado, n8n llama al backend en http://localhost:8000 y se juzga el mp4 escrito en ./output, sin configurar un webhook hacia una URL privada y sin ningún POST de publicación. Primera pasada con la imagen CPU. Hace falta GEMINI_API_KEY o LLM_BASE_URL; no activar ElevenLabs ni fal.ai para este corte.

El material es un vídeo en español con permiso, y no se sube a ninguna plataforma. El listón de frases completas es más estricto que el snap a palabra: hay que anotar si alguna frase queda partida. La transcripción parte de small/int8/CPU con idioma autodetectado, no fijado a «es». En encuadre, una cara tiende a TRACK y varias o ninguna a GENERAL; si el plano es gameplay, SCREENCAST hay que encenderlo porque viene apagado. El mp4 tiene que llevar los subtítulos quemados. El tiempo se cronometra en esa misma pieza, en CPU y solo si se quiere en GPU, sin tomar como resultado propio los 5–8 minutos ni los ~50 segundos. Incertidumbre de hardware: no está dicho si 6 GB bastan; el único umbral escrito de VRAM es el de 8 GB para large-v3-turbo en fp16. Incertidumbre de coste: no hay precios; sí hay salida a Gemini salvo LLM local, y un vídeo mudo la exige igual.

### Riesgos

La dependencia es un main activo, sin tag al que fijar el despliegue, todavía fork de Autocrop-vertical, con el grueso de commits reciente en un contribuidor que no es el owner. [S5] La MIT no cubre cloud/ ni los pesos YOLOv8n (AGPL-3.0 o Enterprise); ofrecer el bloque cloud/ como servicio de pago a terceros queda fuera sin acuerdo escrito. [S4][S6]

Incertidumbre de derechos: nada de lo revisado autoriza a clipear o monetizar VODs ajenos. El permiso del streamer es aparte de la licencia del programa, y la prueba no debe usar el camino de publicación. En privacidad, la transcripción por defecto es local, pero la elección de momentos sale a Gemini si no hay LLM_BASE_URL, y un vídeo sin habla se envía igual porque el sustituto de solo texto no ve la imagen. [S10]

## Fuentes

- [S1] "OpenShorts: Free AI Clip Maker & Clipping Tool, Open Source" — https://www.openshorts.app/ (comprobado de forma independiente contra la homepage y la API del repo: https://www.openshorts.app/)
- [S2] "OpenShot Video Editor | About Us" — https://www.openshot.org/about/
- [S3] "GitHub API: mutonby/openshorts" — https://api.github.com/repos/mutonby/openshorts (comprobado contra las APIs de mutonby, agusmakmun y jnMetaCode: https://api.github.com/repos/mutonby/openshorts)
- [S4] "OpenShorts Commercial License (cloud/LICENSE)" — https://raw.githubusercontent.com/mutonby/openshorts/main/cloud/LICENSE
- [S5] "GitHub commits API: mutonby/openshorts" — https://api.github.com/repos/mutonby/openshorts/commits?per_page=3 (comprobado contra commits, releases, tags e issues: https://api.github.com/repos/mutonby/openshorts/commits/main)
- [S6] "Dockerfile y requirements.txt de mutonby/openshorts" — https://raw.githubusercontent.com/mutonby/openshorts/main/Dockerfile (comprobado contra la doc de YOLOv8 y el Dockerfile: https://raw.githubusercontent.com/ultralytics/ultralytics/main/docs/en/models/yolov8.md)
- [S7] "openshorts/docker-compose.yml (main)" — https://raw.githubusercontent.com/mutonby/openshorts/main/docker-compose.yml
- [S8] "openshorts/app.py webhook y cola (main)" — https://raw.githubusercontent.com/mutonby/openshorts/main/app.py
- [S9] "openshorts main.py, subtitles.py, scene_detection.py, transcribe_backends.py" — https://raw.githubusercontent.com/mutonby/openshorts/main/main.py (comprobado contra subtitles.py, transcribe_backends.py, scene_detection.py y main.py: https://raw.githubusercontent.com/mutonby/openshorts/main/subtitles.py)
- [S10] "openshorts/main.py y README (claves)" — https://raw.githubusercontent.com/mutonby/openshorts/main/main.py (comprobado contra main.py y llm_backend.py: https://raw.githubusercontent.com/mutonby/openshorts/main/main.py)
- [S11] "OpenShorts README, sección GPU" — https://raw.githubusercontent.com/mutonby/openshorts/main/README.md (comprobado contra el README y transcribe_backends.py: https://raw.githubusercontent.com/mutonby/openshorts/main/README.md)
- [S12] "openshorts/examples/n8n/README.md" — https://raw.githubusercontent.com/mutonby/openshorts/main/examples/n8n/README.md
- [S13] "clip_selection.py (snap_clip_to_words, build_transcript_windows)" — https://raw.githubusercontent.com/mutonby/openshorts/main/clip_selection.py (comprobado contra clip_selection.py, gemini_worker.py y How it works: https://raw.githubusercontent.com/mutonby/openshorts/main/gemini_worker.py)
- [S14] "transcribe_backends.py y subtitles.py (faster-whisper)" — https://raw.githubusercontent.com/mutonby/openshorts/main/transcribe_backends.py (comprobado contra transcribe_backends.py y subtitles.py: https://raw.githubusercontent.com/mutonby/openshorts/main/transcribe_backends.py)
- [S15] "main.py (MediaPipe/YOLOv8) y camera_inset.py" — https://raw.githubusercontent.com/mutonby/openshorts/main/main.py (comprobado contra reframe_v2.py, screencast_layout.py y la página de Twitch: https://raw.githubusercontent.com/mutonby/openshorts/main/screencast_layout.py)
- [S16] "subtitles.py burn_subtitles" — https://raw.githubusercontent.com/mutonby/openshorts/main/subtitles.py
- [S17] "Twitch Clip Maker | OpenShorts" — https://www.openshorts.app/platforms/twitch (comprobado contra esa página y twitch_signals.py: https://www.openshorts.app/platforms/twitch)
- [S18] "OpenShorts: How It Works" — https://www.openshorts.app/how-openshorts-works
- [S19] "mutonby/openshorts main.py download_youtube_video" — https://github.com/mutonby/openshorts/blob/main/main.py (comprobado contra el raw: https://raw.githubusercontent.com/mutonby/openshorts/main/main.py)
- [S20] "mutonby/openshorts clip_selection.py" — https://github.com/mutonby/openshorts/blob/main/clip_selection.py (comprobado contra main.py y clip_selection.py: https://raw.githubusercontent.com/mutonby/openshorts/main/clip_selection.py)
- [S21] "mutonby/openshorts scene_detection.py" — https://github.com/mutonby/openshorts/blob/main/scene_detection.py (comprobado contra el raw: https://raw.githubusercontent.com/mutonby/openshorts/main/scene_detection.py)
- [S22] "mutonby/openshorts main.py analyze_scenes_strategy" — https://github.com/mutonby/openshorts/blob/main/main.py (comprobado contra analyze_scenes_strategy y requirements.txt: https://raw.githubusercontent.com/mutonby/openshorts/main/requirements.txt)

## Cobertura e incertidumbres

- Question 1: no hay evidencia pública que identifique la cuenta mutonby con victorcavero14 ni con el contacto jc.caverogracia@gmail.com de cloud/LICENSE; el copyright de la raíz solo dice «OpenShorts».
- Question 1: no existe un GitHub Release de la aplicación. El único paquete versionado encontrado es el CLI de PyPI openshorts 0.1.0, subido el 2026-08-05, cuyo código fuente apunta al mismo repositorio.
- Question 1: la licencia MIT del núcleo no elimina la AGPL-3.0 de Ultralytics/YOLOv8. El repositorio no declara una licencia Enterprise, así que el uso comercial de una compilación que incluya ese modelo puede estar limitado.
- Question 1: no se leyeron los términos de Gemini, ElevenLabs, fal.ai ni de Parakeet (NVIDIA, opcional y solo en imagen GPU); el repositorio no fija su licencia.
- Question 1: Autocrop-vertical sigue siendo el parent de GitHub y no está archivado, pero su último push es del 2026-02-15, así que «vigente» describe el linaje, no un upstream que se actualice al ritmo de OpenShorts.
- Question 1: el recuento open_issues de la API del repositorio era 10 e incluye pull requests; 5 y 46 proceden de la búsqueda de issues y pueden no estar sincronizados al instante.
- Question 2: ningún archivo leído dice si una GTX/RTX 2060 de 6 GB entra en CUDA con large-v3-turbo más TransNetV2/YOLO o acaba en el reintento CPU. El único umbral escrito de «basta» es 8 GB.
- Question 2: no hay presupuesto de disco ni mención de CachyOS; no se puede afirmar que ~300 GB sobre o falten.
- Question 2: no hay Compose ni guía que una n8n en Docker con un runner Python en el host y volúmenes compartidos. localhost:8000 desde el contenedor de n8n no es el host, y un webhook_url privado lo rechaza assert_public_url.
- Question 2: el README lista fal.ai, ElevenLabs y Upload-Post como «required» en Requirements, pero el código solo los usa en AI Shorts, doblaje y POST /api/social/post.
- Question 2: los precios de planes (12/29/59 USD) y de APIs están escritos en el README y en openshorts.app; no se comprobaron como tarifas vigentes.
- Question 2: el ejemplo n8n verifica la firma con JSON.stringify($json.body); el servidor firma los bytes crudos del body, así que esa comparación puede no coincidir.
- Question 3: no hay una prueba visual ni un test citado que demuestre que los clips exportados nunca terminan a mitad de frase; el snap solo garantiza borde de palabra.
- Question 3: no se inspeccionó un issue, discusión o demo que mida calidad de transcripción en español, solo el soporte de código y un comentario interno de Parakeet que menciona audio ES.
- Question 3: no se verificó en ejecución si un YouTube /live/ aún en emisión se descarga: el prefijo live se acepta como URL de un solo vídeo y no apareció un rechazo is_live.
- Question 3: SCREENCAST_LAYOUT y el backend Parakeet no son el camino por defecto; el encuadre de gameplay y el ASR en GPU dependen de flags o de la imagen con GPU.
- Question 4: no se ejecutó un directo en curso. El comentario revisado habla de un livestream ya terminado y sin duración, no de grabar mientras emite.
- Question 4: no hay en el código inspeccionado una medición de que estos cortes mejoren el contexto o la calidad editorial de los vídeos reales de este pipeline.
- Question 4: no aparece YuNet ni un detector de movimiento equivalente al plan pendiente; el seguimiento de cara sirve para encuadrar, no para decidir el corte por movimiento.
- Question 4: importar openshorts-content-machine.json sí programa POST /api/social/post; no publicar solo está garantizado si se usa el flujo de webhook sin ese paso.
- Question 5: no aparece en el código revisado un rechazo explícito de un directo aún en emisión. yt-dlp podría descargar una URL /live si la plataforma la sirve, pero solo está documentado el caso de un livestream ya terminado.
- Question 5: no hay en el README ni en app.py una medición de pared ni de VRAM para una GPU de 6 GB; 8 GB es la cifra que el proyecto declara suficiente para large-v3-turbo fp16 más la detección.
- Question 5: aislar el ensayo del workflow D del pipeline propio no es un flag de OpenShorts; depende de no apuntar ese orquestador a esta instancia.
- Question 5: la calidad de frase completa y el encuadre 9:16 no tienen un umbral numérico en el código; solo se pueden puntuar mirando el transcript y el mp4 que genere ese único trabajo.
- Question 6: no está documentado en la licencia ni en los términos si un streamer concreto autoriza recortar o monetizar su directo. No se revisaron los términos de Twitch, YouTube, Kick u otra plataforma de origen, y no cabe cerrar si publicar sería lícito.
- Question 6: la política de privacidad del 2026-09-04 dice que el chequeo screencast sube el archivo de vídeo completo a Gemini; el screencast_layout.py actual de main envía JPEG y describe la subida del archivo entero como sustituida. No se contrastó la fecha de ese cambio con la de la política.
- Question 6: subprocessors.md deja sin verificar, fuera del repositorio, si la clave Gemini gestionada del cloud es de un proyecto de pago y si los DPA de ElevenLabs, fal.ai y Namecheap están firmados; no se comprobó ese estado real.
- Question 6: el recuento de contributors no mide mantenimiento futuro ni demuestra un solo mantenedor humano. mutonby y victorcavero14 son cuentas distintas, y no hay un SLA en las licencias.
- Question 6: no se auditó cada llamada del árbol. Con claves opcionales de ElevenLabs, fal.ai, Upload-Post o S3, el autoalojado también puede sacar audio, imagen o el clip terminado; el README sí lo indica para esas funciones.
- Question 6: los términos de Gemini exigen usar solo Paid Services al poner API Clients a disposición de usuarios del EEE, Suiza o el Reino Unido. No está resuelto en las fuentes de OpenShorts si una instancia interna entra en ese supuesto.
- 12 afirmaciones candidatas, mal formadas o por encima del tope, se excluyeron antes de la verificación.
- La afirmación claim-18 se excluyó en la verificación: la adquisición es una URL de yt-dlp o un fichero ya en disco, y requirements.txt lista yt-dlp sin Streamlink, pero ninguna fuente citada dice que Streamlink y OBS se conserven ni que OpenShorts solo complemente esa etapa.
- La afirmación claim-23 se excluyó en la verificación: sí hay subtítulos quemados con faster-whisper, word timestamps, ASS y el filtro ffmpeg ass/subtitles, «es» en el contrato y en los 25 idiomas de Parakeet, y la publicación es otro paso. Ninguna fuente consultada muestra subtítulos placeholder que se sustituyan por esos captions.

