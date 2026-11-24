# Todo por Balandro: pulsar y ver, filas de TMDb (23/11/2026)

> **DECISIÓN FINAL DEL USUARIO (23/11/2026): sustituir la fuente, nada más.** El menú de la caja se queda EXACTO
> (secciones, filas, nombres, orden y aspecto: Inicio = Estrenos, Series nuevas, Deportes hoy, Mis favoritos;
> Películas = Estrenos, Recién añadidas, Géneros; Series = Nuevos episodios, Nuevas series, Géneros; Favoritos = Mis
> favoritos). Solo cambia de dónde sale cada fila: de Palantir a su equivalente en Balandro, siempre al día
> (`balandro.FILAS`): Estrenos = catálogo de PasateATorrent por fecha de estreno; Recién añadidas / Nuevos episodios
> = ese catálogo en su orden; Nuevas series = catálogo de series por fecha; Géneros = géneros de PasateATorrent
> (películas) y SeriesPapayaTo (series). La lupa busca en TMDb (`lupa.py`, como el buscador de Balandro) con el
> catálogo de Palantir de reserva. Pulsar una película la reproduce; una serie abre temporadas y capítulos con arte
> de TMDb (`series.py`). Nada de filas nuevas: «Seguir viendo», «Series en seguimiento», TMDb por plataforma y la
> comprobación de fondo de este documento quedan DESCARTADAS. Hecho en 1.0.14, menú sin cambios (MENU_VERSION 10).
>
> **Después (23/11/2026, probado en la caja):** mínimo 1080p y castellano, nada por debajo ni sin calidad conocida
> (`calidad.py`, arreglo de Balandro en `patches.py`); los torrents se ven por AllDebrid (`debrid.py`, ResolveURL),
> no por Elementum (se quedaba sin gente compartiendo); si AllDebrid no lo tiene, lo prepara por detrás y avisa.
> Fuentes: solo torrents en castellano (`balandro.CASTELLANO`; PasateATorrent y DonTorrent primero, este con su reto
> y el arreglo de su búsqueda). Palantir queda de reserva cuando no hay 1080p en castellano. La caja usa DNS de
> Cloudflare (la operadora bloquea DonTorrent y otras). Las filas nunca esperan a Balandro.
>
> **Noche del 23/11/2026 (probado):** fuente principal **Torrentio** (Wolfmax4k y MejorTorrent, castellano, 1080p y 4K;
> `torrentio.py`) por AllDebrid: Tony, La sustancia, Reacher 4x01 y Ted Lasso 4x01 arrancan en 7-9 s en 1080p.
> Detrás, Balandro (solo 1080p) y el catálogo de Palantir (`palantir.py`: enlaces de 1fichier que Palantir veía con
> la cuenta de AllDebrid de la caja; **sus dueños los están borrando**, «deleted by its owner»). Series como Netflix:
> temporadas y capítulos emitidos según TMDb, cada uno se busca al pulsarlo. Filas de series desde DonTorrent «Series
> HD». Siguiente idea, pendiente de una prueba: un grupo de Telegram con vídeos subidos como biblioteca propia.
>
> **A probar en la caja (escrito antes):** resolver a la dirección de Balandro (`plugin.RESOLVE_TO_PLUGIN`, plan B
> `Player().play`), cuánto tarda en llenarse cada fila (Balandro busca el arte en TMDb), géneros, la lupa en TMDb y
> temporadas/capítulos (errata de SeriesPapayaTo).

Palantir 3 cerró el 17/11/2026. Su base local dejó de actualizarse el 12/11: las filas («Estrenos», «Recién
añadidas»…) y la lupa salen de ella y ya no cambiarán. Objetivo: que todo funcione con Balandro, sin Palantir, y que
se vea igual de bien (póster y fondo de TMDb).

## Lo que se quiere

1. **Pulsar y ver.** En una fila o en la lupa, pulsar una película la reproduce, sin listas intermedias. Una serie
   abre sus temporadas y capítulos (con fotos de TMDb), y pulsar un capítulo lo reproduce.
2. **Filas al día.** Las de Películas y Series salen de TMDb (España, en español) y solo muestran lo que se puede ver
   en Balandro.
3. **Bonito.** Póster, fondo y logo de TMDb en todo, igual que con Palantir.

## Lo medido (23/11/2026, caja Vontar X4)

- La búsqueda de Balandro en todas sus webs tarda unos 15 s; varias webs a la vez, unos 10 s (la caja se satura). Una
  web sola, unos 2 s.
- Webs con más títulos: películas en PasateATorrent (6 de 7) y Cuevana3Pro (la que faltaba); series en SeriesPapayaTo
  (3 de 3). Ya está en `balandro.FAST`.
- Se reproducen: PasateATorrent vía Elementum (~17 s hasta la imagen) y SeriesPapayaTo (~6 s). Cuevana3Pro y
  EntrePeliculasySeries resolvían a premilkyway.com, que desde la caja no carga.
- Cada resultado de Balandro trae `infoLabels.tmdb_id`: se identifica el título sin depender del nombre.

## Diseño

### 1. Pulsar y ver (`plugin.py`, `balandro.py`)

- Película: elemento reproducible con ruta `?play=peliculas&tmdb=<id>`. Al pulsar:
  1. fuentes de esa película: primero la comprobación ya hecha por el servicio (apartado 3); si no hay, las webs
     rápidas (~2-6 s); si tampoco, la búsqueda en todas las webs (~15 s, con aviso «Buscando en más webs…»);
  2. se resuelve a la dirección de Balandro de la primera fuente (`setResolvedUrl`). Balandro elige servidor y
     reproduce, con Elementum si es torrent;
  3. si no está en ningún sitio: aviso «No está disponible» y nada más.
- Si la fuente elegida falla (servidor caído), el siguiente intento de esa película usa la fuente siguiente: el
  plugin apunta qué fuente probó y el servicio la da por buena cuando empieza el vídeo (`onAVStarted`).
- Serie: carpeta `?temporadas=<id>` → temporadas de la web de Balandro que la tiene, con póster de cada temporada de
  TMDb → `?capitulos=…` → capítulos con su foto, título y resumen de TMDb (una consulta a TMDb por temporada,
  guardada). Pulsar un capítulo lo reproduce igual que una película.
- **A comprobar en la caja:** que Kodi 21 acepte resolver a una dirección de otro addon (`plugin://plugin.video.
  balandro/…`). Si no, el plan B es resolver en falso y lanzar `Player().play()` con esa dirección.

### 2. Filas de TMDb (`tmdb_filas.py`, nuevo)

Consultas a TMDb con `language=es-ES` y `region=ES`:

| Sección | Fila | Consulta |
|---|---|---|
| Películas | Estrenos | `discover/movie`: estreno digital o físico en España (tipos 4 y 5) en los últimos 120 días, por fecha |
| Películas | Populares | `movie/popular` |
| Películas | Mejor valoradas | `movie/top_rated` |
| Películas | Géneros | fila de géneros; cada uno abre `discover/movie?with_genres=` por popularidad |
| Series | Nuevos episodios | `tv/on_the_air` |
| Series | Populares | `tv/popular` |
| Series | Mejor valoradas | `tv/top_rated` |
| Series | Géneros | como en Películas |
| Inicio | Estrenos, Series nuevas | las de arriba |

- Cada fila toma unos 60 candidatos (3 páginas) y enseña los 20 primeros **disponibles**, en el orden de TMDb.
- El servicio renueva las listas de TMDb cada 6 horas. El plugin sirve la fila desde la copia (<1 s), como ahora.
- Arte: póster w500, fondo w1280 y logo (`/images`, español o inglés) de TMDb. Con `tmdb` en uniqueids, AF3 (TMDb
  Helper) completa lo que falte, como hacía con Palantir.

### 3. Comprobación de disponibilidad (servicio, de fondo)

- Cola: todos los candidatos de las filas sin comprobar o caducados. Se comprueba un título cada vez con las webs
  rápidas (2-6 s), solo cuando la caja está tranquila (sin mando 20 s y sin vídeo a pantalla completa; lo mismo que
  ya usa `filas.Refresher`).
- Resultado guardado por título (`disponibles.json`): las fuentes encontradas. Vale 7 días si está y 2 si no (los
  estrenos tardan en subirse).
- Primer llenado: ~6 filas × 60 = 360 títulos × ~4 s ≈ 25 min de caja tranquila. Las filas van apareciendo según se
  comprueban. Después solo se comprueba lo nuevo.
- De regalo: al pulsar algo de una fila, las fuentes ya están y empieza sin buscar.

### 4. La lupa

- Pasa a buscar en TMDb (`search/multi`, ~0,5 s, siempre al día) en vez de en el catálogo congelado de Palantir, con
  el mismo arte. Al pulsar, apartado 1: si no está en Balandro, aviso.
- Se quita el índice del catálogo de Palantir (`catalogo.IndexKeeper`).

### 5. El menú

- Las filas de Películas y Series dejan de depender de las rutas de Palantir: son fijas (`fila_url('peliculas.
  estrenos')`…) y las sirve el asistente desde TMDb. Deportes (BlackGhost) no cambia. `MENU_VERSION` 11: las cajas
  lo vuelven a aplicar al arrancar.
- Palantir deja de usarse. Desinstalarlo queda para después, cuando todo esto funcione.

## Orden de trabajo

1. Pulsar y ver (películas y series) desde la lupa actual. Se prueba en la caja: reproducción, plan B si hace falta.
2. Comprobación de disponibilidad + filas de TMDb + menú 11.
3. Lupa en TMDb.

Todo con pruebas en el Mac (módulos puros, como el resto). En la caja solo se instala y se prueba cuando esté libre:
las pruebas lanzan Balandro y Elementum, y parar el vídeo es inevitable para probar la reproducción.

## Riesgos

- Que una web de `FAST` caiga o cambie: la comprobación lo nota (deja de encontrar) y la búsqueda en todas las webs
  sigue de reserva. Cambiar el orden es tocar `FAST`.
- Estrenos muy recientes que aún no ha subido ninguna web: no salen hasta que estén. Es lo que se busca.
- La clave de TMDb ya está en los ajustes del asistente.
