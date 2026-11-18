# La lupa con la búsqueda de Arctic Fuse 3 y el catálogo de Palantir — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que la lupa abra la búsqueda propia de Arctic Fuse 3, con dos filas (Películas y Series) sacadas del catálogo de Palantir en 1–2 s, y que al elegir un resultado Palantir lo reproduzca como siempre.

**Architecture:** skinvariables (la búsqueda de AF3) pide sus fuentes como rutas con `{query}`. Las dos fuentes son una ruta nueva del asistente (`plugin.py ?buscar=`):
- busca en un índice propio (SQLite), hecho a partir de la base de Palantir y abierto en solo lectura;
- devuelve elementos cuya ruta es la ficha de Palantir codificada (`selectvideos_` / `listado_temporadaS`).

La lupa recupera su acción original de AF3, y los textos que faltan en español se añaden con parches.

**Tech Stack:** Python 3 (3.9 en los tests, 3.11 en la caja), `sqlite3`, Kodistubs 21 y pytest. Kodi 21.3 con Arctic Fuse 3 3.5.4 y skinvariables.

**Spec:** `docs/superpowers/specs/2026-11-18-lupa-busqueda-skin-design.md`

## Global Constraints

- Tests desde `src/script.papa.inicio`: `../../venv/bin/python -m pytest -q ../../tests`. Código válido en Python 3.9: sin `match` ni `X | Y` en tipos.
- Los módulos de `resources/lib` son puros: Kodi entra inyectado o por `kodi_setup` / `plugin.py`, como en `filas.py` y `favoritos.py`.
- La base de Palantir solo se lee: `sqlite3.connect('file:%s?mode=ro' % path, uri=True)`. No se escribe ni se toca nada de Palantir.
- Rutas candidatas de la base de Palantir, en este orden:
  1. `special://home/addons/plugin.video.palantir3/moria.cm3`
  2. `special://profile/addon_data/script.module/settings.xml`
- Índice propio en `special://profile/addon_data/script.papa.inicio/catalogo.db`.
- Títulos que entran: `pelis.categoria = 'Película'` y `series.categoria IN ('General','Retro','Reality')`, en ambos casos con al menos un enlace (`enlaces_pelis` / `enlaces_series`).
- Búsqueda: subcadena del título normalizado, mínimo 2 caracteres normalizados, máximo **60** por fila. Primero los que empiezan por el texto y luego alfabético.
- Textos exactos (de la spec):

  | Archivo | Id | Texto |
  |---|---|---|
  | AF3 | 31850 | Resultados |
  | AF3 | 31851 | Fuentes |
  | AF3 | 31852 | Década |
  | AF3 | 31861 | Sin resultados |
  | AF3 | 31863 | Busca |
  | AF3 | 31864 | películas y series |
  | AF3 | 31865 | Escribe lo que quieres ver. |
  | skinvariables | 32099 | Década |
  | skinvariables | 32100 | Todos |
  | skinvariables | 32104 | Buscando «{}» |

  Las filas de búsqueda se llaman **Películas** y **Series**.
- Nunca en el repo: la clave de AllDebrid ni el código de BlackGhost. No usar HTTP 8080. En la caja no se borra nada sin preguntar.
- Versión del addon **1.0.13**, `MENU_VERSION = 10`.
- Rama `feat/lupa-skin` desde `main`. El usuario fusiona la PR.

## Review Focus

1. **Textos con apóstrofos, acentos, ñ o comodines** («O'Brien», «SEÑOR», «100%_»): no rompen el SQL y se comparan normalizados como en Palantir (ñ→N, sin puntuación). Test en la tarea 2.
2. **Palantir sin instalar o sin base descargada**: las filas salen vacías, sin excepción ni diálogo. Tests en las tareas 2 y 3.
3. **Primera búsqueda tras cambiar la base de Palantir, con las dos filas pidiéndose a la vez**: el índice se rehace en un archivo temporal y se reemplaza de golpe; nunca se lee a medias. Test en la tarea 2.
4. **Texto vacío o solo signos** («  », «¿?»): lista vacía al momento. Test en la tarea 2.
5. **Fichas incompletas** (sin carátula, fondo, logo, fecha o tráiler; nota sin «/» o vacía): el elemento se monta igual. Test en la tarea 1.

---

### Task 1: Fichas de Palantir (`catalogo.py`, parte pura)

**Files:**
- Create: `src/script.papa.inicio/resources/lib/catalogo.py`
- Create: `tests/test_catalogo.py`

**Interfaces:**
- Produces:
  - `normalize(text: str) -> str` — como `map_string` de Palantir:
    - recorta los espacios del principio y del final;
    - cada carácter ≤ U+00FF que sea letra o dígito pasa a su letra base ASCII en mayúscula (á→A, ñ→N, ç→C);
    - el espacio se queda; el resto se quita (puntuación y caracteres > U+00FF).
  - `p3_url(fields: dict) -> str` — `'plugin://plugin.video.palantir3/?' + p3_encode('{%s}' % ', '.join('"%s": %r' % (k, fields[k]) for k in sorted(fields)))`.
  - `p3_encode(text: str) -> str` — el `p3b64encode` de Palantir:
    1. `v = base64.b64encode(text.encode())`; `q = int(len(v) / 4)`, contado **antes** de quitar los `=`;
    2. se quitan los `=`;
    3. se devuelve `urllib.parse.quote(v[:q][::-1] + v[q:][::-1])`.
  - `p3_decode(value: str) -> str` — la inversa, solo para tests:
    1. `unquote`;
    2. `q = int(n / 4)`, con `n` la longitud tras rellenar hasta múltiplo de 4;
    3. se invierten las dos partes y se añaden los `=` al final antes de `b64decode`.
  - `to_item(kind: str, row: dict) -> dict` — `kind` es `'peliculas'` o `'series'`. `row` trae las claves `tmdb, titulo, fecha, plot, poster, fondo, duration, mpaa, genero, trailer, clearlogo, rating`; en series falta `duration`. Devuelve un dict con la forma de `filas.to_item`: `{'label', 'path', 'folder', 'art', 'info', 'uniqueids', 'properties'}`.

- [ ] **Step 1: Write the failing tests**

```python
from resources.lib import catalogo as cat

def test_normalize_is_palantirs_map_string():
    assert cat.normalize('  La ballena ') == 'LA BALLENA'
    assert cat.normalize('Señor de los Anillos') == 'SENOR DE LOS ANILLOS'
    assert cat.normalize("Spider-Man: O'Brien ¿Qué?") == 'SPIDERMAN OBRIEN QUE'
    assert cat.normalize('Película 1917') == 'PELICULA 1917'
    assert cat.normalize('東京 ok') == 'OK'  # > U+00FF se quita; el espacio inicial que queda, también

def test_p3_url_round_trips_like_palantir():
    url = cat.p3_url({'tmdb': '1', 'action': 'selectvideos_', 'title': 'Ñ'})
    assert url.startswith('plugin://plugin.video.palantir3/?')
    assert cat.p3_decode(url.split('?', 1)[1]) == '{"action": \'selectvideos_\', "title": \'Ñ\', "tmdb": \'1\'}'

MOVIE = {'tmdb': 785084, 'titulo': 'La ballena', 'fecha': '2022-12-09', 'plot': 'P', 'poster': '/p.jpg',
         'fondo': '/f.jpg', 'duration': 7020, 'mpaa': '16', 'genero': 'Drama#Familia', 'trailer': 'Rhd5EyZ-rEs',
         'clearlogo': '/l.png', 'rating': '7.9/7.7'}

def test_movie_item_plays_through_palantir():
    it = cat.to_item('peliculas', MOVIE)
    assert it['label'] == 'La ballena' and it['folder'] is False
    assert it['properties'] == {'IsPlayable': 'true'}
    assert it['art'] == {'poster': 'https://image.tmdb.org/t/p/w500/p.jpg', 'thumb': 'https://image.tmdb.org/t/p/w500/p.jpg',
                         'fanart': 'https://image.tmdb.org/t/p/w1280/f.jpg', 'clearlogo': 'https://image.tmdb.org/t/p/w500/l.png'}
    assert it['info'] == {'title': 'La ballena', 'year': 2022, 'premiered': '2022-12-09', 'plot': 'P', 'duration': 7020,
                          'mpaa': '16', 'genre': ['Drama', 'Familia'], 'rating': 7.9, 'mediatype': 'movie',
                          'trailer': 'plugin://plugin.video.youtube/play/?video_id=Rhd5EyZ-rEs'}
    assert it['uniqueids'] == {'tmdb': '785084'}
    fields = eval(cat.p3_decode(it['path'].split('?', 1)[1]))
    assert fields['action'] == 'selectvideos_' and fields['content'] == 'movies' and fields['tmdb'] == '785084'
    assert fields['isPlayable'] is True and fields['title'] == fields['label'] == 'La ballena'

def test_series_item_opens_palantirs_seasons():
    row = {k: v for k, v in MOVIE.items() if k != 'duration'}
    it = cat.to_item('series', dict(row, titulo='The Pitt'))
    fields = eval(cat.p3_decode(it['path'].split('?', 1)[1]))
    assert it['folder'] is True and it['properties'] == {} and it['info']['mediatype'] == 'tvshow'
    assert fields['action'] == 'listado_temporadaS' and fields['content'] == 'tvshows'
    assert fields['tvshowtitle'] == fields['label'] == 'The Pitt' and fields['page'] == 0

def test_incomplete_rows_still_make_an_item():  # Review Focus 5
    bare = {'tmdb': 1, 'titulo': 'X', 'fecha': None, 'plot': None, 'poster': None, 'fondo': '', 'duration': None,
            'mpaa': None, 'genero': None, 'trailer': None, 'clearlogo': None, 'rating': '6.5'}
    it = cat.to_item('peliculas', bare)
    assert it['art'] == {} and it['info'] == {'title': 'X', 'rating': 6.5, 'mediatype': 'movie'}
    assert cat.to_item('peliculas', dict(bare, rating=''))['info'] == {'title': 'X', 'mediatype': 'movie'}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src/script.papa.inicio && ../../venv/bin/python -m pytest -q ../../tests/test_catalogo.py`
Expected: FAIL (`ModuleNotFoundError` / `catalogo`).

- [ ] **Step 3: Implement `normalize`, `p3_encode`, `p3_decode`, `p3_url` and `to_item` in `catalogo.py`**

Cabecera del módulo: explica que lee el catálogo de Palantir (su código está ofuscado y es lento al arrancar, ~4,5 s) y monta sus fichas.

En `normalize`, usar `unicodedata.normalize('NFKD', ch)[0]` para la letra base.

`to_item`:
- **Imágenes**: `https://image.tmdb.org/t/p/` + tamaño + ruta (carátula w500, fondo w1280, logo w500). `thumb` igual que la carátula. Si la ruta ya empieza por `http`, se deja tal cual. Las vacías no se ponen.
- **Info**: `year` = `int(fecha[:4])` y `premiered` = `fecha`. `rating` = `float` de lo que hay antes de `/`; si no es un número, no se pone.
- **Campos de la ficha (`fields`)**:
  - comunes: `label`, `tmdb` (str), `fecha`, `plot`, `poster`, `fanart` (= fondo), `clearlogo`, `mpaa` (`''` si falta) y `rating`;
  - película: `title`, `duration`, `action='selectvideos_'`, `content='movies'`, `isPlayable=True`;
  - serie: `tvshowtitle`, `action='listado_temporadaS'`, `content='tvshows'`, `page=0`.

  No se incluyen claves con valor `None`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_catalogo.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git checkout -b feat/lupa-skin
git add docs/superpowers/specs/2026-11-18-lupa-busqueda-skin-design.md docs/superpowers/plans/2026-11-18-lupa-busqueda-skin.md src/script.papa.inicio/resources/lib/catalogo.py tests/test_catalogo.py
git commit -m "feat: fichas de Palantir para la búsqueda de la skin (1.0.13)"
```

### Task 2: Índice y búsqueda (`catalogo.py`, SQLite)

**Files:**
- Modify: `src/script.papa.inicio/resources/lib/catalogo.py`
- Modify: `tests/test_catalogo.py`

**Interfaces:**
- Consumes: `normalize`, `to_item` (tarea 1).
- Produces:
  - `KINDS = {'peliculas': ('pelis', 'enlaces_pelis', ('Película',)), 'series': ('series', 'enlaces_series', ('General', 'Retro', 'Reality'))}`
  - `LIMIT = 60`
  - `MIN_CHARS = 2`
  - `stamp(db_path: str) -> str` — `'%d-%d' % (int(st.st_mtime), st.st_size)`.
  - `build_index(db_path: str, index_path: str, db_stamp: str) -> None` — escribe en `index_path + '.' + uuid4().hex[:8] + '.tmp'` y luego `os.replace`. Tablas `titulos(kind, tmdb, norm)` y `meta(stamp)`.
  - `index_current(index_path: str, db_stamp: str) -> bool`
  - `search(index_path: str, kind: str, text: str, limit: int = LIMIT) -> list` — devuelve tmdb int; parámetros con `?`, nunca formateo de texto.
  - `details(db_path: str, kind: str, tmdbs: list) -> list` — dicts en el mismo orden que `tmdbs`.
  - `find(db_path, index_path: str, kind: str, text: str) -> list` — dicts de `to_item`; `[]` si `db_path` es None, `kind` no está en `KINDS` o el texto es corto. Rehace el índice si no está al día.

- [ ] **Step 1: Write the failing tests**

Fixture `palantir_db(tmp_path)`: una base SQLite con las tablas `pelis` y `series` (columnas de la tarea 1 más `categoria`) y `enlaces_pelis(tmdb)` / `enlaces_series(tmdb)`. Contenido:
- películas: «La ballena» (1, Película, con enlace), «Una ballena» (2, Película, con enlace), «Ballena sin enlace» (3, Película, sin enlace), «Ballena animada» (4, Dibujo, con enlace), «Señor O'Brien» (5, Película, con enlace) y 70 películas «Ballena 001»…«Ballena 070» (100–169, Película, con enlace);
- series: «The Pitt» (10, General, con enlace) y «Pitt novela» (11, Novela, con enlace).

```python
def test_search_finds_what_palantir_finds(palantir_db, tmp_path):
    idx = str(tmp_path / 'catalogo.db')
    pelis = cat.find(palantir_db, idx, 'peliculas', 'ballena')
    titles = [i['label'] for i in pelis]
    assert 'Ballena sin enlace' not in titles and 'Ballena animada' not in titles   # como sus vistas
    assert len(pelis) == cat.LIMIT                                                  # 72 coinciden, 60 salen
    assert titles[0].startswith('Ballena 0') and 'La ballena' not in titles[:50]    # primero los que empiezan
    assert [i['label'] for i in cat.find(palantir_db, idx, 'series', 'pitt')] == ['The Pitt']

def test_quotes_accents_and_wildcards_are_safe(palantir_db, tmp_path):  # Review Focus 1
    idx = str(tmp_path / 'catalogo.db')
    assert [i['label'] for i in cat.find(palantir_db, idx, 'peliculas', "señor o'brien")] == ["Señor O'Brien"]
    assert cat.find(palantir_db, idx, 'peliculas', '100%_') == []

def test_short_or_empty_text_returns_nothing(palantir_db, tmp_path):  # Review Focus 4
    idx = str(tmp_path / 'catalogo.db')
    for text in ('', '  ', '¿?', 'a'):
        assert cat.find(palantir_db, idx, 'peliculas', text) == []
    assert cat.find(None, idx, 'peliculas', 'ballena') == []   # Review Focus 2
    assert cat.find(palantir_db, idx, 'otra', 'ballena') == []

def test_index_is_rebuilt_when_palantir_changes_and_replaced_at_once(palantir_db, tmp_path, monkeypatch):  # Review Focus 3
    idx = str(tmp_path / 'catalogo.db')
    cat.find(palantir_db, idx, 'series', 'pitt')
    assert cat.index_current(idx, cat.stamp(palantir_db))
    assert not cat.index_current(idx, 'otro-sello') and not cat.index_current(str(tmp_path / 'no'), 'x')
    replaced = []
    real = os.replace
    monkeypatch.setattr(cat.os, 'replace', lambda a, b: (replaced.append((a, b)), real(a, b)))
    cat.build_index(palantir_db, idx, 'nuevo')
    assert replaced and replaced[0][1] == idx and replaced[0][0].endswith('.tmp')
    assert not [p for p in os.listdir(str(tmp_path)) if p.endswith('.tmp')]

def test_palantir_db_is_only_read(palantir_db, tmp_path):
    before = open(palantir_db, 'rb').read()
    cat.find(palantir_db, str(tmp_path / 'catalogo.db'), 'peliculas', 'ballena')
    assert open(palantir_db, 'rb').read() == before
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_catalogo.py`
Expected: FAIL (`find` no existe).

- [ ] **Step 3: Implement `KINDS`, `LIMIT`, `MIN_CHARS`, `stamp`, `build_index`, `index_current`, `search`, `details` and `find`**

- **Orden de `search`**: `ORDER BY CASE WHEN norm LIKE ? || '%' THEN 0 ELSE 1 END, norm`, con el filtro `kind = ? AND norm LIKE '%' || ? || '%'`. El texto normalizado no lleva `%` ni `_` porque `normalize` los quita.
- **`details`**: `SELECT … FROM <tabla> WHERE tmdb IN (?,?,…)` y luego se ordena en Python según `tmdbs`.
- **Errores de SQLite** (base rota o sin tablas): `find` devuelve `[]`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_catalogo.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/script.papa.inicio/resources/lib/catalogo.py tests/test_catalogo.py
git commit -m "feat: índice propio del catálogo de Palantir (búsqueda en milisegundos)"
```

### Task 3: Ruta `?buscar=` del asistente

**Files:**
- Modify: `src/script.papa.inicio/resources/lib/kodi_setup.py` (constantes y `palantir_db()`)
- Modify: `src/script.papa.inicio/plugin.py` (`listar_busqueda`, `main` y docstring)
- Test: `tests/test_kodi_glue.py`

**Interfaces:**
- Consumes: `catalogo.find` (tarea 2) y `plugin._fila_item(item)` (ya existe).
- Produces:
  - `ks.PALANTIR_DB = ('special://home/addons/plugin.video.palantir3/moria.cm3', 'special://profile/addon_data/script.module/settings.xml')`
  - `ks.CATALOGO = PROFILE + 'catalogo.db'`
  - `ks.palantir_db() -> str or None` — ruta traducida (`xbmcvfs.translatePath`) de la primera que exista (`xbmcvfs.exists`).
  - Ruta del plugin: `plugin://script.papa.inicio/?buscar=<peliculas|series>&q=<texto>`.

- [ ] **Step 1: Write the failing test**

```python
def test_palantir_db_prefers_the_addon_file_then_the_profile_copy(monkeypatch):  # Review Focus 2
    monkeypatch.setattr(ks.xbmcvfs, 'translatePath', lambda p: '/k/' + p.split('://', 1)[1])
    for present, expected in (({ks.PALANTIR_DB[0], ks.PALANTIR_DB[1]}, '/k/home/addons/plugin.video.palantir3/moria.cm3'),
                              ({ks.PALANTIR_DB[1]}, '/k/profile/addon_data/script.module/settings.xml'),
                              (set(), None)):
        monkeypatch.setattr(ks.xbmcvfs, 'exists', lambda p, s=present: p in s)
        assert ks.palantir_db() == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_kodi_glue.py -k palantir_db`
Expected: FAIL (`palantir_db` no existe).

- [ ] **Step 3: Implement `palantir_db()` and `plugin.listar_busqueda(handle, kind, text)`**

`listar_busqueda`:
1. `catalogo.find(ks.palantir_db(), xbmcvfs.translatePath(ks.CATALOGO), kind, text)`;
2. añade cada elemento con `_fila_item` (`isFolder=item['folder']`);
3. `setContent(handle, filas.content(items))` y `endOfDirectory(handle, cacheToDisc=False)`;
4. registra con `ks.log` `'buscar %s %r: %d en %.2fs'`.

En `main`: `elif params.get('buscar'): listar_busqueda(handle, params['buscar'], params.get('q', ''))`. Documentar la ruta nueva en el docstring de `plugin.py`.

- [ ] **Step 4: Run tests**

Run: `../../venv/bin/python -m pytest -q ../../tests`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add src/script.papa.inicio/resources/lib/kodi_setup.py src/script.papa.inicio/plugin.py tests/test_kodi_glue.py
git commit -m "feat: el asistente sirve las búsquedas de Películas y Series desde el catálogo"
```

### Task 4: Fuentes de búsqueda en el menú (`menus.py`)

**Files:**
- Modify: `src/script.papa.inicio/resources/lib/menus.py`
- Test: `tests/test_menus.py`

**Interfaces:**
- Produces:
  - `menus.SEARCH = 'plugin://script.papa.inicio/?buscar=%s&q={query}'`
  - `build_preset(rutas)['skinvariables-shortcut-searchwidgets.json']`
  - `MENU_VERSION = 10`

- [ ] **Step 1: Write the failing tests**

```python
def test_search_hub_has_palantir_movies_and_series_only():
    files = m.build_preset(RUTAS)          # la RUTAS que ya usa test_menus
    assert files[m.FILE % 'searchwidgets'] == [
        {'label': 'Películas', 'icon': 'special://skin/extras/icons/film.png',
         'path': 'plugin://script.papa.inicio/?buscar=peliculas&q={query}', 'target': 'videos', 'widget_style': 'Poster'},
        {'label': 'Series', 'icon': 'special://skin/extras/icons/tv.png',
         'path': 'plugin://script.papa.inicio/?buscar=series&q={query}', 'target': 'videos', 'widget_style': 'Poster'}]

def test_search_has_no_tmdb_discover_rows_and_menu_is_rebuilt():
    assert 'Skin.SetBool(HomeSwitcher.Search.DisableDiscover)' in m.skin_builtins(RUTAS, '/p', 'now')
    assert m.MENU_VERSION == 10
```

- [ ] **Step 2: Run to verify they fail**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_menus.py`
Expected: FAIL

- [ ] **Step 3: Implement**

- `build_preset` escribe `files[FILE % 'searchwidgets']` siempre, con las dos entradas.
- En `skin_builtins`, `Skin.SetBool(HomeSwitcher.Search.DisableDiscover)` va antes de `copy_menufolder`. Es un `SetBool` a verdadero, nunca un `Skin.String` (ver la memoria `kodi-skin-string-crea-ajuste`).
- `MENU_VERSION = 10`, con la línea de comentario `# 10: la lupa abre la búsqueda de AF3 con Películas y Series del catálogo de Palantir.`

- [ ] **Step 4: Run tests**

Run: `../../venv/bin/python -m pytest -q ../../tests`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/script.papa.inicio/resources/lib/menus.py tests/test_menus.py
git commit -m "feat: la búsqueda de AF3 busca en Películas y Series del asistente"
```

### Task 5: Parches (la lupa original y los textos en español)

**Files:**
- Modify: `src/script.papa.inicio/resources/lib/patches.py`
- Modify: `src/script.papa.inicio/resources/lib/kodi_setup.py` (`SKINVARIABLES`, `PATCHES`)
- Test: `tests/test_patches.py`, `tests/test_kodi_glue.py`

**Interfaces:**
- Produces:
  - `patches.AF3_SEARCH_ACTION` — la línea original: `<param name="action">RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,progress_dialog$VAR[Value_MultiSearch_Layout_Param]$VAR[Value_MultiSearch_Discover_Param])</param>`.
  - `patches.patch_af3_search(text) -> str or None` — ahora cambia `<param name="action">RunScript(script.papa.inicio,buscar)</param>` por `AF3_SEARCH_ACTION`. Devuelve None si no está.
  - `patches.add_strings(text, strings: dict) -> str or None`, con `strings = {id: (msgid, msgstr)}`:
    - si existe `msgctxt "#id"` con `msgstr ""`, rellena el msgstr;
    - si no existe, añade al final `\nmsgctxt "#id"\nmsgid "…"\nmsgstr "…"\n`;
    - si ya está traducido, no lo toca;
    - devuelve None si no cambia nada.
  - `patches.AF3_STRINGS_FILE = 'language/resource.language.es_es/strings.po'` y `patches.AF3_STRINGS` con los ids 31850–31865 de las Global Constraints.
  - `patches.SKINVARIABLES_STRINGS_FILE = 'resources/language/resource.language.es_es/strings.po'` y `patches.SKINVARIABLES_STRINGS` con 32099, 32100 y 32104. El msgid de 32104 es `Searching \"{}\"`, escapado como en el `.po`.
  - `patches.patch_af3_strings(text)` y `patches.patch_skinvariables_strings(text)`, que llaman a `add_strings`.
  - `ks.SKINVARIABLES = 'script.skinvariables'`; `PATCHES` gana dos entradas, `(SKIN, AF3_STRINGS_FILE, patch_af3_strings, lambda v: True)` y `(SKINVARIABLES, SKINVARIABLES_STRINGS_FILE, patch_skinvariables_strings, lambda v: True)`.

- [ ] **Step 1: Write the failing tests**

En `test_patches.py`, sustituye `test_search_patch_makes_the_magnifier_search_in_palantir` y `test_search_patch_is_applied_once_and_ignores_other_skins` por:

```python
PATCHED_HOME = AF3_HOME.replace(AF3_HOME.splitlines()[4].strip(), '<param name="action">RunScript(script.papa.inicio,buscar)</param>')

def test_search_patch_gives_the_magnifier_back_to_af3():
    assert pt.patch_af3_search(PATCHED_HOME) == AF3_HOME
    assert pt.patch_af3_search(AF3_HOME) is None and pt.patch_af3_search('<includes/>') is None

PO = 'msgctxt "#31016"\nmsgid "Sort by"\nmsgstr "Ordenar por"\n\nmsgctxt "#31851"\nmsgid "Sources"\nmsgstr ""\n'

def test_missing_spanish_texts_are_added_once():
    new = pt.patch_af3_strings(PO)
    assert 'msgctxt "#31851"\nmsgid "Sources"\nmsgstr "Fuentes"' in new
    assert 'msgctxt "#31865"\nmsgid "Enter a search term to begin."\nmsgstr "Escribe lo que quieres ver."' in new
    assert new.count('msgctxt "#31851"') == 1 and 'msgstr "Ordenar por"' in new
    assert pt.patch_af3_strings(new) is None
    sv = pt.patch_skinvariables_strings('')
    assert 'msgctxt "#32104"\nmsgid "Searching \\"{}\\""\nmsgstr "Buscando «{}»"' in sv and 'msgstr "Todos"' in sv
```

En `test_kodi_glue.py`:

```python
def test_patches_cover_the_search_texts_of_af3_and_skinvariables():
    targets = {(a, f) for a, f, _, _ in ks.PATCHES}
    assert (ks.SKIN, pt.AF3_STRINGS_FILE) in targets and ('script.skinvariables', pt.SKINVARIABLES_STRINGS_FILE) in targets
```

- [ ] **Step 2: Run to verify they fail**

Run: `../../venv/bin/python -m pytest -q ../../tests/test_patches.py ../../tests/test_kodi_glue.py`
Expected: FAIL

- [ ] **Step 3: Implement** — el comentario del parche de la lupa dice que deshace el de la 1.0.12.

- [ ] **Step 4: Run tests**

Run: `../../venv/bin/python -m pytest -q ../../tests`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/script.papa.inicio/resources/lib/patches.py src/script.papa.inicio/resources/lib/kodi_setup.py tests/test_patches.py tests/test_kodi_glue.py
git commit -m "feat: la lupa vuelve a ser la de AF3 y sus textos salen en español"
```

### Task 6: Retirar la lupa de la 1.0.12

**Files:**
- Delete: `src/script.papa.inicio/resources/lib/buscar.py`, `tests/test_buscar.py` (aprobado por el usuario)
- Modify: `src/script.papa.inicio/default.py`
- Modify: `src/script.papa.inicio/resources/lib/discover.py` (quitar `BUSCAR_POR_TITULO` y `result['buscar']`)
- Modify: `tests/test_discover.py` (quitar `test_palantir_search_by_title_is_found_for_the_magnifier`)

**Interfaces:**
- Produces: `default.py` con `sys.argv[1] == 'buscar'` abre la búsqueda de AF3: `RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,progress_dialog,mediatype_lists,no_all_list,no_discover)`. Así cubre el rato entre que se actualiza el asistente y la skin se recarga sin el parche viejo; sin esto, la lupa abriría el menú del asistente.

  Desviación pequeña de la spec, que decía quitar la entrada: queda como redirección de una línea.

- [ ] **Step 1: Write the failing test** (en `test_kodi_glue.py`, junto a los que ya compilan `default.py`):

```python
def test_old_magnifier_action_opens_the_af3_search():
    src = open(os.path.join(ADDON_DIR, 'default.py'), encoding='utf-8').read()
    assert 'run_multisearch' in src and 'buscar_en_palantir' not in src
    assert not os.path.exists(os.path.join(ADDON_DIR, 'resources', 'lib', 'buscar.py'))
```

- [ ] **Step 2: Run to verify it fails** — `../../venv/bin/python -m pytest -q ../../tests/test_kodi_glue.py -k old_magnifier`
- [ ] **Step 3: Implement** — `git rm` de los dos archivos y los cambios de arriba.
- [ ] **Step 4: Run tests** — `../../venv/bin/python -m pytest -q ../../tests` → PASS
- [ ] **Step 5: Commit**

```bash
git add -A src/script.papa.inicio tests
git commit -m "refactor: retirar la lupa de la 1.0.12 (teclado autocompletado de Palantir)"
```

### Task 7: Versión, documentación y prueba en la caja

**Files:**
- Modify: `src/script.papa.inicio/addon.xml` (version `1.0.13`)
- Modify: `GUIA.md`:
  - en la chuleta, la fila de la lupa;
  - en «Si algo falla», la fila de la lupa sin resultados;
  - quitar la fila «Al volver con Atrás desde una serie sale otra vez el teclado de Palantir», que ya no aplica.
- Modify: `docs/superpowers/specs/2026-11-16-kodi-papa-design.md` (sección «La lupa (1.0.13)», que remite a la spec nueva)
- Regenerate: `docs/zips` con `python3 tools/build_repo.py`. Si solo cambian las fechas de los zips de `repository.papa`, restaurarlos con `git checkout`.

- [ ] **Step 1: Docs, version and repo zip; tests** — `../../venv/bin/python -m pytest -q ../../tests` → PASS.
- [ ] **Step 2: Deploy to the box**
  1. `Application.Quit`; si a los 40 s sigue vivo, `am force-stop`.
  2. `adb push` de `addon.xml`, `default.py`, `plugin.py` y `resources/lib/{catalogo,kodi_setup,menus,patches,discover}.py`, y `su 0 rm` de `resources/lib/buscar.py` en la caja (archivo nuestro que deja de existir).
  3. Comparar md5 con el repo.
  4. Arrancar Kodi y esperar `menu_version` = 10.
- [ ] **Step 3: Verify on the box** (comprobación de la spec):
  1. La lupa abre la búsqueda de AF3, con los textos en español tras la recarga de la skin.
  2. «pitt» da Películas (1) y Series (1); «ballena», solo Películas (4); un texto sin resultados, «Sin resultados».
  3. Medir en el log (`buscar … en …s`) y en pantalla. Objetivo: las filas en 1–2 s.
  4. Elegir película → enlaces de Palantir → se reproduce; parar → vuelta a la búsqueda.
  5. Elegir serie → temporadas; Atrás → búsqueda.
  6. Escribir con las letras en pantalla y con el teclado completo.
- [ ] **Step 4: Commit, push and PR** (el usuario fusiona):

```bash
git add -A GUIA.md docs src tests
git commit -m "docs: la lupa con la búsqueda de AF3 y el catálogo de Palantir (1.0.13)"
git push -u origin feat/lupa-skin
gh pr create --base main --title "feat: la lupa con la búsqueda de Arctic Fuse 3 y el catálogo de Palantir (1.0.13)"
```
