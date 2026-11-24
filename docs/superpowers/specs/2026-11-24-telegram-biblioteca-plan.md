# Telegram como biblioteca (tipo Palantir) — plan

24/11/2026. Fuente: grupo-foro de Telegram (temas **Películas** y **Series**). Objetivo: que su contenido aparezca y se
reproduzca desde el menú actual del asistente, **sin cambiar el diseño** (mismas filas, nombres, orden y aspecto),
con las mismas reglas: **1080p o más, castellano, nada de calidad desconocida**, y al día solo.

## Lo que ya sabemos (fase 0, hecha)

- Películas: 10.112 vídeos; ~3.800 en 1080p/4K (3.169 comprobados por resolución + 655 por el nombre).
  Nombres buenos: «Longlegs (2024).mp4» → 3.148 con título y año.
- Series: 54.254 capítulos; ~16.500 en 1080p/4K. 12.560 nombres no se entienden con el lector actual, pero casi
  todos por formatos que se pueden leer: «1x06 - Snowpiercer [x265].mkv» (título detrás), «Quién mató a Sara? T3
  CAPITULO 3», «T-8/E-96», «Veronika 1 x 2». Los mensajes seguidos son de la misma serie (sirven de contexto).
- Caja: plugin.video.telegram 1.7.0 instalado y con sesión. Cada vídeo es
  `http://127.0.0.1:8765/t<token>/stream/<grupo>/<mensaje>/video.mp4`.
  Prueba 1080p: imagen a los 12,5 s, sin cortes, salto al 50 % en 3,8 s.
- Leer el grupo entero tarda horas (Telegram entrega ~500 mensajes cada 10 min): la carga inicial se hace una vez
  (ya está: `~/.config/kodi-papa/fase0_videos.json`); luego solo lo nuevo.

## Arquitectura

```
Mac (una vez)                         Caja (siempre)
fase0_videos.json ──► indexar ──►  telegram.db (SQLite)  ◄── servicio: cada noche, mensajes nuevos
                     (TMDb)            │                         (API local del addon de Telegram)
                                       ▼
                     lupa · fichas · reproducir · filas ──► 127.0.0.1:8765/stream/… ──► Kodi
```

`telegram.db` (en addon_data del asistente, como el catálogo de Palantir):
- `pelis(tmdb, titulo, año, msg, calidad, gb, idioma, subido)` — varias versiones por título.
- `capitulos(tmdb_serie, temporada, capitulo, msg, calidad, gb, subido)`.
- `estado(ultimo_msg)` para la actualización.

## Fases

### 1. Indexador (en el Mac, código en `resources/lib/telegram_idx.py`, puro y con pruebas)
1. **Leer nombres** — ampliar `parse_name`: «1x06 - Título», «T3 CAPITULO 3», «T-8/E-96», «1 x 2», «Cap.102»,
   «Temporada 2 Capítulo 5»; quitar firmas (@canal, [by …], wolfmax4k…). Para un capítulo sin título, heredar la
   serie del mensaje anterior/siguiente si coincide la numeración.
2. **Cruzar con TMDb** (es-ES): películas por título+año (sin año, solo si hay un único resultado claro);
   series por nombre, una vez por serie (caché). Rechazar coincidencias dudosas → se registran para revisarlas.
3. **Calidad** — por resolución si la hay; si no, por el nombre (1080/2160/4K); si no, por **GB por hora con la
   duración de TMDb** (misma regla que ya usamos: ≥ 1,6 GB/h). Lo que quede dudoso se descarta.
4. **Idioma** — descartar catalán, VOSE, latino, subtitulado, alemán (marcas en nombre/texto). El grupo es en
   castellano; el resto se da por bueno.
5. **Elegir versión** — por título/capítulo: 1080p antes que 4K (va más fluido por Wi-Fi), luego el de tamaño
   razonable; se guardan 2–3 alternativas por si una falla.
6. Medir: cuántas películas y series quedan, y un muestreo a mano de 30 aciertos/fallos de TMDb.

### 2. En la caja: reproducir (`resources/lib/telegram.py`)
- Leer el token del addon de Telegram y montar la URL; comprobar antes que el servicio responde (`api/status`).
- Integrarlo en `reproducir` como una fuente más (orden: ver decisiones). Si un vídeo falla (borrado por el
  grupo), probar la alternativa y marcarlo.
- Precarga (`api/prefetch`) del principio al abrir la ficha, para bajar de 12,5 s.
- Pruebas en la caja: 3 películas y 3 capítulos (arranque, 1 min sin cortes, salto), siempre con la caja libre.

### 3. En la caja: catálogo
- **Lupa**: lo de Telegram entra en los resultados (ya buscan por TMDb, así que basta con que haya fuente).
- **Series** al estilo Netflix (como ahora): temporadas y capítulos de TMDb; el capítulo se reproduce desde
  Telegram si está, si no, desde las otras fuentes.
- **Filas**: no se añade ninguna. Opcional (decisión): que «recién añadidas» use también lo último del grupo.

### 4. Mantenerlo al día (servicio del asistente)
- Cada noche (y nunca con la caja reproduciendo): pedir al addon de Telegram los vídeos más nuevos del grupo
  hasta `ultimo_msg`, indexarlos en la caja (mismo código de la fase 1) y guardarlos.
- Problema: la API del addon no dice de qué tema es cada mensaje. Opciones: (a) deducirlo (nombre con
  temporada/capítulo → serie; título+año en TMDb movie → película) o (b) parchear el addon (como ya hacemos con
  Balandro/YouTube en `patches.py`) para que devuelva el tema. Preferida: (b), con (a) de respaldo.

### 5. Riesgos
- **El grupo puede desaparecer** (Telegram cierra grupos de este tipo): las otras fuentes siguen; el catálogo se
  marcaría vacío. Mitigación: no depender solo de él.
- **Cuenta de Telegram**: descargar mucho con una cuenta personal puede provocar esperas (FloodWait) y, en casos
  extremos, avisos. El uso de una persona viendo cosas es normal; la carga inicial ya está hecha.
- **Addon de terceros**: versión 1.7.0 fijada, sin el binario precompilado y sin repositorio activo; las
  actualizaciones se revisan a mano.
- **Velocidad**: 12,5 s de arranque frente a 6–8 s de Torrentio/PeLiS.

## Decisiones del usuario (24/11/2026)
1. **Orden en `reproducir`**: Torrentio/PeLiS primero; Telegram justo después. Mientras se pregunta a
   Torrentio/PeLiS, si el título está en `telegram.db` se precarga ya su principio (`api/prefetch`), para que si
   ellos fallan Telegram arranque sin sumar su espera. (El usuario pidió ayuda para decidir; se le recomendó esto
   por velocidad —se quejó de 15 s— y porque lo de AllDebrid no desaparece; la calidad es la misma.)
2. **Filas**: sí, lo nuevo del grupo se mezcla en las filas de «recién añadidas» que ya existen (sin crear filas
   ni cambiar nombres, orden ni aspecto).
3. **Parche del addon de Telegram**: permitido (fase 4 b), en `patches.py`, con copia del original.
4. **Sin mínimo de resolución en Telegram** (24/11/2026, tras ver la fase 1): «todos los vídeos son de buena
   calidad». Entra todo lo que esté en castellano; la calidad queda como etiqueta (4K/1080p/720p/SD/?) y solo
   ordena las versiones de un mismo título (1080p, 4K, ?, 720p, SD).
5. **Estrenos ≠ Recién añadidas** (24/11/2026): «Estrenos» solo películas de este año (si en enero hay menos de
   10, también las del año anterior); «Recién añadidas», de cualquier año. Telegram se mezcla en las dos y en
   «Nuevos episodios».
