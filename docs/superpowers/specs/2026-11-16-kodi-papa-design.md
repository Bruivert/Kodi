# Kodi de Papá — Arctic Fuse 3 + Palantir + BlackGhost (Vontar X4, Kodi 21 Omega)

## Contexto

El padre del usuario no se aclara con la skin por defecto de Kodi (Estuary). Queremos que al encender la Vontar X4 vea algo tipo **Apple TV/Netflix**: fondo grande con la imagen de la película, filas de carátulas y un menú corto:

**Inicio · Películas · Series · Novedades · Deportes**

- Películas, Series y Novedades salen de **Palantir** (ya vinculado a AllDebrid en la caja).
- Deportes tiene subsecciones sacadas de **BlackGhost**: Fútbol, Baloncesto, NFL, Pádel, Fórmula 1, MotoGP y UFC.
  - **Cambio de la 1.0.10 (17/11/2026):** BlackGhost 8.0.66 no tiene carpetas por deporte; ordena por fuentes ("agendas" y listas de canales). Las filas son: Agenda de hoy (AGENDA DEPORTESPLUS sin "+", en hora de España; si no, AGENDA LIVE o cualquier agenda), Partidos en España (AGENDA DEL DIA CIRACO, Acestream), Fútbol/Baloncesto/NFL/Motor/UFC (las carpetas de AGENDA NSPORTS), Fórmula 1 en español (Formula 1 Replays) y Canales Acestream (ACESTREAM MIXTO, que el padre ya tenía en favoritos). Pádel no existe.
  - El código (p. ej. `n17`) va dentro de las rutas (`0-deportes.php?n17`); con uno caducado salen vacías. Se guarda en el ajuste `bg_codigo` del asistente, que lo escribe en `addon_data/plugin.video.blackghost/codeservernew.txt` (BlackGhost entra con él sin preguntar, aunque sea temporal). Si el código cambia, el servicio vuelve a buscar las filas y rehace el menú. Nunca se abre BlackGhost desde el servicio sin código guardado: "INGRESAR AL ADDON" abriría un teclado.
- El código de BlackGhost cambia cada cierto tiempo y se saca de su Telegram (el enlace o QR aparece dentro del propio addon). Al usuario le gustaría que eso fuera automático.
- **Favoritos**: el padre guarda lo que le gusta y lo encuentra en un sitio fijo.
- En Películas y Series se ve la **valoración de IMDb**.
- **Tráileres automáticos en español de España** (nada de latino).

Restricciones descubiertas:
- Esta sesión es en la nube: no llega a la caja, y Remote Control con el Mac no está disponible para la cuenta. Las webs de Palantir, BlackGhost (`site27.xyz`) y Telegram están bloqueadas desde aquí. La caja sí tiene internet normal.
- Por eso **el paquete descubre en la propia caja** cómo están organizados Palantir y BlackGhost por dentro, en vez de llevar las rutas internas escritas a mano.
- El repo `Bruivert/Kodi` es privado. El usuario lo hará **público** y activará **GitHub Pages**. Ahí solo va la configuración: nunca la clave de AllDebrid ni el código de BlackGhost.

Decisiones del usuario: skin **Arctic Fuse 3** (rama omega de jurialmunkey, v3.5.x), entrega como **paquete desde GitHub con actualizaciones automáticas** y repo público.
Supuesto (lo indicó al principio): Palantir y BlackGhost ya están instalados y funcionando. La guía incluye una comprobación por si no lo están.

## Cómo funciona Arctic Fuse 3 (verificado leyendo su código)

- Los menús se guardan como JSON de `script.skinvariables` en `special://profile/addon_data/script.skinvariables/nodes/<skin>/skinvariables-shortcut-*.json`. Si no existen, usa los que trae la skin en `special://skin/shortcuts/`.
- Archivos de un "preset" (ejemplo: `shortcuts/presets/tmdbhelper/` en el repo de la skin):
  - `skinvariables-shortcut-hubs.json`: secciones del menú principal (ventanas 1101–1109, cada una con `label`, `icon`, `window`, `slot` y `disabled`).
  - `skinvariables-shortcut-<ventana>widgets.json`: filas de carátulas de cada sección (`label`, `path` plugin://, `target: videos`, `widget_style`).
  - `skinvariables-shortcut-<ventana>submenu.json`: submenú de cada sección.
  - `skinvariables-shortcut-homewidgets.json` y `homesubmenu.json`: la pantalla de Inicio.
- La propia skin aplica un preset con `RunScript(script.skinvariables,copy_menufolder=<carpeta>/,skin=<SkinFolder>,force=True)` y después `Skin.SetString(Shortcuts.RebuildDateTime,…)` (archivo `shortcuts/builtins/skinvariables-setupwizard-preset.json`). **Reutilizaremos exactamente ese mecanismo** con nuestra carpeta generada.
- Las dependencias (`script.skinvariables`, `plugin.video.themoviedb.helper`, `script.texturemaker`, recursos) están en el repo de jurialmunkey para Omega: `https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/`.

## Diseño

### 1. Repositorio Kodi propio (publicado con GitHub Pages)
- `repository.papa`: un `addon.xml` con dos `<dir>`.
  - El nuestro: `https://bruivert.github.io/Kodi/zips/`.
  - El de jurialmunkey para Omega (`minversion="20.9.1"`), para que al instalar el asistente Kodi descargue sola la skin Arctic Fuse 3 y sus dependencias.
- `tools/build_repo.py` genera `docs/`: los zips, `addons.xml`, `addons.xml.md5` y un `index.html` que Kodi puede navegar como fuente.

### 2. Addon `script.papa.inicio` ("Kodi de Papá — Asistente")
- `addon.xml` declara como dependencias `skin.arctic.fuse.3`, `script.skinvariables`, `plugin.video.themoviedb.helper` y `xbmc.python 3.0.1`.
- Menú del asistente, pensado para el hijo, no para el padre:
  1. **Configurar todo**
     - Pone Kodi en español y España.
     - Cambia la skin a Arctic Fuse 3 por JSON-RPC (`lookandfeel.skin`). Hay que pulsar "Sí" en el aviso de Kodi.
     - Salta el asistente de bienvenida de la skin.
     - Pide las claves gratuitas de OMDb y TMDb, o las salta si no las tienes todavía.
     - Configura TMDb Helper (es-ES y OMDb) y pone IMDb como primera valoración en la skin.
     - Descubre los menús, genera el preset y lo aplica.
  2. **Actualizar menús**: vuelve a descubrir los menús, por si Palantir o BlackGhost cambian.
  3. **Diagnóstico**: crea `informe-kodi.txt` y lo copia a un pendrive si hay uno conectado, o si no lo muestra en pantalla.
     - Incluye: versiones, IDs de los addons, menús de Palantir y BlackGhost hasta 2 niveles (nombre y ruta), enlaces de Telegram encontrados en los archivos de BlackGhost y los **nombres** de sus ajustes.
     - **Nunca incluye** valores de ajustes, tokens ni la clave de AllDebrid.
- `resources/lib/discover.py`
  - Busca Palantir y BlackGhost entre los addons instalados (`Addons.GetAddons`, por nombre).
  - Recorre sus menús con `Files.GetDirectory`.
  - Empareja cada carpeta por palabras clave. Antes de comparar, quita acentos, mayúsculas y etiquetas `[COLOR]`/`[B]`.
    - Películas: populares, estrenos o en cines, mejor valoradas, géneros.
    - Series: populares, en emisión, mejor valoradas.
    - Novedades: estrenos de películas y novedades de series.
    - Deportes: futbol/laliga · baloncesto/nba/acb · nfl/futbol americano · padel · formula 1/f1 · motogp/motociclismo · ufc/mma, y además "agenda"/"hoy"/"directo" si existe.
  - Si alguna carpeta no se reconoce, sale **una lista para elegirla a mano**.
  - Las rutas elegidas se guardan en `addon_data/script.papa.inicio/rutas.json`. Si BlackGhost pide el código durante el recorrido, se mete una vez.
- `resources/lib/menus.py`: genera los JSON con el mismo formato que los presets de la skin.
  - Secciones: 1101 Películas, 1102 Series, 1103 Novedades, 1104 Deportes y un hub libre para Favoritos. El resto (calendario, TV en directo, addons…) queda **desactivado** para que el menú sea corto.
  - Deportes: una fila por deporte y un submenú con los mismos deportes, que abre la carpeta a pantalla completa.
  - Inicio: filas de "Estrenos", "Series nuevas" y "Deportes hoy" (agenda, si existe).
- Ajustes ligeros para la X4: TMDb Helper en es-ES, pocas filas por sección (4–6 como máximo) y nada de fondos animados.

### 3. Código de BlackGhost automático (fase 2, según lo que salga del diagnóstico)
- Un servicio de nuestro addon lee el enlace de Telegram desde los archivos de BlackGhost en la caja.
  - Si es un **canal público** (`t.me/s/<canal>`), busca el código en el último mensaje cada vez que arranca Kodi y cada 6 h.
  - Si BlackGhost **guarda el código en sus ajustes**, lo escribe ahí.
- Si el canal es privado o el código solo se mete en una ventana al abrir el addon, no se puede automatizar del todo. En ese caso, al caducar, al padre le sale un aviso claro ("Deportes necesita un código nuevo, avisa a tu hijo") y el hijo lo mete como ahora.
- Necesito el informe de diagnóstico de la caja para cerrar esta parte. Hasta entonces Deportes funciona metiendo el código a mano.

### 4. Favoritos
- **Cambio de la 1.0.10:** la fila no lee `favourites://` (solo trae nombre y miniatura: sin fanart ni ficha, la sección salía con fondo liso). La da `plugin://script.papa.inicio/?lista=favoritos` (plugin.py): lee favourites.xml y, a los que tienen año (los de Palantir), les pone la ficha de TMDb (`search/multi`, título y año; tipo, id, fanart, sinopsis), guardada en `favoritos_tmdb.json`. Al pulsar hace lo mismo que el favorito (carpeta, PlayMedia u orden). "Mis favoritos" es la primera fila de Inicio: Kodi carga las filas de 3 en 3 y en orden, y pasar por las secciones con el foco encarga todas sus filas (por eso Deportes tiene 5 filas y el resto en botones).
- Se usan los favoritos nativos de Kodi (`favourites://`). Sirven igual para películas y series de Palantir que para canales o eventos de BlackGhost.
- Nueva sección **Favoritos** en el menú (Inicio · Películas · Series · Novedades · Deportes · Favoritos) y una fila "Mis favoritos" en Inicio.
  - Usará un hub libre de Arctic Fuse 3, por ejemplo el 1108 con `HomeSwitcher.1108.Type=Custom`. Lo confirmo al implementar.
- Para añadir algo, el padre mantiene pulsado OK (o pulsa el botón de menú) → "Añadir a favoritos". La guía tendrá una chuleta de una línea para él.

### 5. Valoración de IMDb en Películas y Series
- Arctic Fuse 3 muestra las valoraciones que le pasa TMDb Helper. Ya lo comprobé: hay ajustes `CustomRating.Movies.Item0X` y `CustomRating.TVShows.Item0X`.
- La nota de IMDb la consigue TMDb Helper con una **clave gratuita de OMDb** (ajuste `omdb_apikey`).
- El asistente pide la clave una vez y la guarda solo en la caja. Además pone IMDb como primera valoración en películas y series.
- Para escribir la clave con el móvil en vez de con el mando: app **Kore** (oficial de Kodi).
- Riesgo: TMDb Helper tiene que reconocer los elementos de Palantir (por ID de IMDb/TMDb o por título y año). Lo confirmará el diagnóstico.

### 6. Tráileres automáticos en español de España
- Comprobado en el código: TMDb Helper pide los vídeos a TMDb con idioma `es,null,en`, **sin filtrar por país**. Puede coger un tráiler latino.
- Por eso el servicio de nuestro addon resuelve el tráiler por su cuenta:
  - Cuando el foco se queda unos 4 s en una película o serie, consulta la API de TMDb (`/videos`).
  - Se queda solo con `iso_639_1=es` **y `iso_3166_1=ES`** y tipo "Trailer", prefiriendo los oficiales.
  - Lo reproduce de fondo con el addon de YouTube.
  - Se para al mover el foco o al darle a reproducir.
  - Primero, siempre, uno en español de España. Nunca sale uno latino.
  - **Si no hay ninguno en castellano** (cambio de la 1.0.10, pedido por el usuario el 17/11/2026): el vídeo de TMDb en el idioma original de la película, o en inglés, como la web de TMDb. Prioridad: tráiler, después teaser, después clip. No se usa si falló la red al preguntar por los de España.
- Necesita una **clave gratuita de TMDb**, que se mete igual que la de OMDb.
- Se puede activar o desactivar desde el asistente.
- Riesgo: el addon de YouTube a veces pide claves propias para reproducir. Lo compruebo en la caja y, si hace falta, la guía explica cómo ponerlas.

### 7. Guía `GUIA.md` (español, paso a paso con el mando)
1. Hacer público el repo y activar Pages (main → `/docs`).
2. Sacar las claves gratuitas de OMDb (omdbapi.com) y TMDb (themoviedb.org → Ajustes → API) e instalar Kore en el móvil.
3. En Kodi: activar "Orígenes desconocidos" y añadir la fuente `https://bruivert.github.io/Kodi/`.
4. Instalar desde zip `repository.papa`, y luego desde el repositorio "Kodi de Papá — Asistente".
5. Abrir el asistente → "Configurar todo".
6. Cómo actualizar los menús, cómo sacar el diagnóstico y la chuleta de Favoritos para tu padre.

## Estructura del repo
```
src/repository.papa/addon.xml, icon.png
src/script.papa.inicio/addon.xml, default.py, service.py, resources/lib/{discover,menus,kodi_setup,diagnostico,trailers,claves}.py,
                       resources/language/resource.language.es_es/strings.po
tools/build_repo.py
docs/                       # salida para GitHub Pages (generada)
tests/                      # pytest
GUIA.md
docs/superpowers/specs/2026-11-16-kodi-papa-design.md   # este diseño guardado en el repo
```
Desarrollo en la rama `claude/brave-keller-iht160`. Pages se publica desde `main` tras fusionar (pediré permiso antes de abrir la PR).

## Verificación
1. **Tests unitarios (pytest)** con un `xbmc` simulado (Kodistubs de PyPI) y respuestas JSON-RPC falsas que imitan menús en español con colores y acentos:
   - El emparejamiento detecta cada deporte y cada lista.
   - Los JSON generados tienen las mismas claves que los presets reales de Arctic Fuse 3 (descargados de raw.githubusercontent.com).
   - Los no reconocidos llevan a la lista de elegir a mano.
   - Selección de tráiler con respuestas `/videos` de ejemplo: escoge es-ES, descarta es-MX, es-419 e inglés, y devuelve "nada" si no hay de España.
   - El hub de Favoritos apunta a `favourites://`.
2. **Build del repo**: `addons.xml` es XML válido, el md5 coincide, los zips tienen la carpeta del addon en la raíz y las versiones están sincronizadas.
3. **Prueba con Kodi real (si se puede instalar Kodi 21 en el contenedor con Xvfb)**:
   - Instalar Arctic Fuse 3 y sus dependencias desde GitHub.
   - Usar addons falsos `plugin.video.palantir3` y BlackGhost con carpetas de ejemplo.
   - Ejecutar "Configurar todo" y hacer una captura del Inicio y de Deportes.
   - Si no se puede, lo digo y queda solo la prueba en la caja.
4. **En la Vontar (con el usuario)**: lista de comprobación.
   - Se ve el menú de 5 secciones.
   - Cada fila carga y una película se reproduce por AllDebrid.
   - La nota de IMDb aparece en una película y en una serie de Palantir.
   - Al quedarse en una película salta su tráiler de España; en una sin tráiler de España no sale nada.
   - Añadir a Favoritos funciona y aparece en la sección y en la fila de Inicio.
   - Cada deporte abre su carpeta.
   - El arranque se mantiene en un tiempo razonable.
   - Diagnóstico enviado para la fase 2.
