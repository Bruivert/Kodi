# -*- coding: utf-8 -*-
"""Todo lo que toca Kodi: JSON-RPC, diálogos, archivos, skin y ajustes de otros addons."""
import json
import re
import time
import uuid

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import balandro, calidad, diagnostico, discover, filas, menus, patches

ADDON_ID = 'script.papa.inicio'
TITLE = 'Kodi de Papá'
SKIN = menus.SKIN
YOUTUBE = 'plugin.video.youtube'
SKINVARIABLES = 'script.skinvariables'
TMDBH = 'plugin.video.themoviedb.helper'
TMDBH_ES_ES = 20  # índice de es-ES en LANGUAGES de TMDb Helper
PROFILE = 'special://profile/addon_data/%s/' % ADDON_ID
PRESET = PROFILE + 'preset/'
RUTAS = PROFILE + 'rutas.json'
PENDING = PROFILE + 'pendiente'
BACKUP = PROFILE + 'backup/'
FILAS = PROFILE + 'filas/'  # copias de las filas de Palantir (filas.py)
FILAS_INDEX = FILAS + 'indice.json'  # 1.0.10: índice común (leer y reescribir); ya no se usa
FILA_KEY = re.compile(r'^[a-z]+\.[a-z0-9]+$')  # "peliculas.estrenos": nada de "../" desde la URL del plugin
ARTE = PROFILE + 'arte_deportes.json'  # fanart de TheSportsDB para Deportes (arte_deportes.py)
INTENTOS = PROFILE + 'intentos.json'  # última fuente probada por ficha y si arrancó (balandro.pick)
CALIDADES = PROFILE + 'calidades.json'  # calidad de cada página de PasateATorrent (calidad.py)
BALANDRO = 'plugin.video.balandro'
TELEGRAM_ADDON = 'plugin.video.telegram'
CATALOGO = PROFILE + 'catalogo.db'  # índice de títulos de Palantir para la lupa (catalogo.py)
TELEGRAM = PROFILE + 'telegram.db'  # vídeos del grupo de Telegram por película/capítulo (telegram.py)
# La base de Palantir, donde la busca su propio código (MoriaDB): la del addon si existe, si no la descargada.
PALANTIR_DB = ('special://home/addons/plugin.video.palantir3/moria.cm3',
               'special://profile/addon_data/script.module/settings.xml')
MENU_VERSION_FILE = PROFILE + 'menu_version'
# Donde BlackGhost guarda el código con el que entra sin preguntarlo (lo lee aunque sea uno temporal, como "n17").
BG_CODE_FILE = 'special://profile/addon_data/plugin.video.blackghost/codeservernew.txt'
INFORME = 'informe-kodi.txt'
NODES = 'special://profile/addon_data/script.skinvariables/nodes/%s/' % SKIN
NONE_LABEL = '— No está / saltar —'


# --- utilidades -------------------------------------------------------------

def log(msg):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), xbmc.LOGINFO)


def notify(msg, ms=4000):
    xbmcgui.Dialog().notification(TITLE, msg, xbmcgui.NOTIFICATION_INFO, ms)


def setting(sid):
    return xbmcaddon.Addon(ADDON_ID).getSetting(sid)


def set_setting(sid, value):
    xbmcaddon.Addon(ADDON_ID).setSetting(sid, value)


def rpc(method, params=None):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params:
        request['params'] = params
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        log('%s -> %s' % (method, response['error']))
        return {}
    return response.get('result') or {}


def write_file(path, text):
    """De una vez: se escribe aparte y se renombra. Un corte de luz o dos escritores a la vez (el plugin y el servicio
    guardando la misma copia) nunca dejan un archivo a medias."""
    xbmcvfs.mkdirs(path.rsplit('/', 1)[0] + '/')
    tmp = '%s.%s.tmp' % (path, uuid.uuid4().hex[:8])
    f = xbmcvfs.File(tmp, 'w')
    try:
        f.write(bytearray(text.encode('utf-8')))
    finally:
        f.close()
    if not xbmcvfs.rename(tmp, path):  # por si el sistema no deja renombrar encima de uno que ya existe
        xbmcvfs.delete(path)
        if not xbmcvfs.rename(tmp, path):
            xbmcvfs.delete(tmp)
            raise IOError('no se pudo escribir %s' % path)


def read_file(path):
    if not xbmcvfs.exists(path):
        return ''
    f = xbmcvfs.File(path)
    try:
        return f.read()
    finally:
        f.close()


def has_addon(addon_id):
    return bool(addon_id) and xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id)


# --- addons -----------------------------------------------------------------

def match_addon(addons, keywords):
    wanted = [discover.normalize(k) for k in keywords]

    def hit(a):
        name = discover.normalize(a.get('name', ''))
        ident = a.get('addonid', '').lower()
        return any(w and (w in name or w.replace(' ', '') in ident) for w in wanted)

    hits = sorted((a for a in addons if hit(a)), key=lambda a: not a.get('enabled', True))
    return hits[0]['addonid'] if hits else None


def find_addon(keywords):
    result = rpc('Addons.GetAddons', {'type': 'xbmc.python.pluginsource', 'properties': ['name', 'enabled']})
    return match_addon(result.get('addons') or [], keywords)


def addon_version(addon_id):
    details = rpc('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['version']}).get('addon') or {}
    return details.get('version', '')


def ensure_addon(addon_id, timeout=600):
    """Instala un addon desde los repositorios (Kodi pide confirmación) y espera a que esté."""
    if has_addon(addon_id):
        return True
    xbmc.executebuiltin('InstallAddon(%s)' % addon_id, True)
    monitor = xbmc.Monitor()
    for waited in range(timeout):
        if has_addon(addon_id):
            return True
        busy = xbmc.getCondVisibility('Window.IsVisible(extendedprogressdialog) | Window.IsVisible(yesnodialog)')
        if waited > 15 and not busy:
            break
        if monitor.waitForAbort(1):
            break
    return has_addon(addon_id)


def list_dir(path):
    files = rpc('Files.GetDirectory', {'directory': path, 'media': 'files'}).get('files') or []
    return [{'label': f.get('label', ''), 'file': f.get('file', ''), 'filetype': f.get('filetype', 'file')}
            for f in files]


def ask(title, labels):
    idx = xbmcgui.Dialog().select(title, list(labels) + [NONE_LABEL])
    return idx if 0 <= idx < len(labels) else -1


# --- idioma, claves y TMDb Helper ------------------------------------------

def ensure_spanish():
    current = rpc('Settings.GetSettingValue', {'setting': 'locale.language'}).get('value', '')
    if current == 'resource.language.es_es':
        return
    if ensure_addon('resource.language.es_es', timeout=120):
        rpc('Settings.SetSettingValue', {'setting': 'locale.language', 'value': 'resource.language.es_es'})


KEYS = [
    ('omdb_key', 'Clave de OMDb (para la nota de IMDb). Vacío = saltar'),
    ('tmdb_key', 'Clave de TMDb v3 (para los tráileres de España). Vacío = saltar'),
    ('bg_codigo', 'Código de BlackGhost (sale en su Telegram, p. ej. n17). Vacío = saltar'),
]


def clean_key(value):
    """La clave sola, también si se pega el enlace de ejemplo de OMDb (http://www.omdbapi.com/?i=…&apikey=XXXX)."""
    value = (value or '').strip()
    found = re.search(r'apikey=([A-Za-z0-9]+)', value)
    return found.group(1) if found else value


def ask_keys():
    dialog = xbmcgui.Dialog()
    for sid, heading in KEYS:
        value = clean_key(dialog.input(heading, defaultt=setting(sid)))
        if value:
            set_setting(sid, value)


# - Idioma: YouTube elige la pista de audio según el suyo (en-US de fábrica) y muchos tráileres españoles traen
#   además el doblaje automático al inglés; sonaba ese. 'es' es el "hl" de YouTube para el español de España.
# - Redirección: pasando el vídeo por su servidor interno, al parar un tráiler Kodi esperaba 20 s a que terminara
#   una descarga y el siguiente no arrancaba. Redirigido, Kodi lo descarga directamente de Google.
YOUTUBE_SETTINGS = (('youtube.language', 'es', lambda v: v[:2] == 'es'),
                    ('youtube.region', 'ES', lambda v: v == 'ES'),
                    ('youtube.http.stream_redirect', 'true', lambda v: v == 'true'))


def apply_youtube_settings():
    if not has_addon(YOUTUBE):
        return False
    youtube = xbmcaddon.Addon(YOUTUBE)
    changed = False
    for sid, value, ok in YOUTUBE_SETTINGS:
        if not ok(youtube.getSetting(sid)):
            youtube.setSetting(sid, value)
            changed = True
    if changed:
        log('YouTube: español de España y vídeo directo de Google')
    return changed


def apply_tmdbhelper():
    if not has_addon(TMDBH):
        return False
    helper = xbmcaddon.Addon(TMDBH)
    try:
        helper.setSettingInt('language', TMDBH_ES_ES)
    except Exception:
        helper.setSetting('language', str(TMDBH_ES_ES))
    omdb = clean_key(setting('omdb_key'))
    if omdb:
        helper.setSetting('omdb_apikey', omdb)
    return True


# --- menús ------------------------------------------------------------------

def load_rutas():
    """Las listas encontradas en Palantir y BlackGhost; 'balandro' dice si está instalado (filas y menú de Balandro)."""
    try:
        rutas = json.loads(read_file(RUTAS) or '{}')
    except ValueError:
        return {}
    if rutas:
        rutas['balandro'] = has_addon(BALANDRO)
    return rutas


def _load_json(path, default):
    try:
        return json.loads(read_file(path) or 'null') or default
    except ValueError:
        return default


def load_fila(key):
    if not FILA_KEY.match(key or ''):
        return None
    return _load_json(FILAS + key + '.json', None)


def load_fila_index():
    """{fila: {'path', 'time'}} sin leer las copias enteras: un .meta pequeño por fila, así dos escritores a la vez
    no se pisan un índice común."""
    try:
        names = xbmcvfs.listdir(FILAS)[1]
    except Exception:
        return {}
    index = {}
    for name in names:
        if name.endswith('.meta'):
            meta = _load_json(FILAS + name, None)
            if meta:
                index[name[:-len('.meta')]] = meta
    return index


def save_fila(key, entry):
    write_file(FILAS + key + '.json', json.dumps(entry, ensure_ascii=False))
    write_file(FILAS + key + '.meta', json.dumps({'path': entry['path'], 'time': entry['time']}))


def palantir_db():
    """Ruta de la base de Palantir, o None si no está (Palantir sin instalar o sin descargar)."""
    for path in PALANTIR_DB:
        if xbmcvfs.exists(path):
            return xbmcvfs.translatePath(path)
    return None


def load_arte():
    return _load_json(ARTE, {})


def save_arte(state):
    write_file(ARTE, json.dumps(state, ensure_ascii=False))


def fetch_text(url):
    """Una página web como texto ('' si falla). requests trae sus certificados: el Python de Kodi en Android a veces no
    tiene los del sistema."""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
    try:
        import requests
        response = requests.get(url, headers=headers, timeout=15)
        return response.text if response.ok else ''
    except ImportError:
        from urllib.request import Request, urlopen
        try:
            with urlopen(Request(url, headers=headers), timeout=15) as response:
                return response.read().decode('utf-8', 'ignore')
        except Exception:
            return ''
    except Exception:
        return ''


def fetch_bytes(url):
    """Un fichero (un .torrent) como bytes, o b'' si falla."""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
    try:
        import requests
        response = requests.get(url, headers=headers, timeout=15)
        return response.content if response.ok else b''
    except Exception:
        return b''


def post_json(url, body, referer):
    """POST con JSON y la respuesta como dict ({} si falla). Para el reto de DonTorrent (plugin.py)."""
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Safari/537.36',
               'Content-Type': 'application/json', 'Referer': referer}
    try:
        import requests
        response = requests.post(url, data=json.dumps(body), headers=headers, timeout=15)
        return response.json() if response.ok else {}
    except Exception:
        return {}


def load_calidades():
    return _load_json(CALIDADES, {})


def save_calidades(cache):
    write_file(CALIDADES, json.dumps(cache, ensure_ascii=False))


def check_pages(kind, urls, cache, now, workers=1):
    """Mira la calidad de las páginas que falten o hayan caducado y la apunta en cache. Devuelve cuántas miró."""
    todo = [u for u in dict.fromkeys(urls) if u and not calidad.fresh(cache.get(u), now)]
    if not todo:
        return 0
    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(workers) as pool:
            pages = list(pool.map(fetch_text, todo))
    else:
        pages = [fetch_text(u) for u in todo]
    for url, html in zip(todo, pages):
        if html:  # sin respuesta no se apunta nada: se vuelve a mirar la próxima vez
            cache[url] = calidad.page_entry(kind, html, now)
    return len(todo)


def fetch_row_hd(path, workers=1, pages=None):
    """Una fila de Balandro con varias páginas de la web (balandro.ROW_PAGES) y la calidad de cada título ya mirada
    (calidades.json), para enseñar solo lo de 1080p o más. Las demás listas, tal cual."""
    files = fetch_row(path)
    kind = balandro.row_kind(path)
    if not files or not kind:
        return files
    following = balandro.next_page(files)
    for _ in range((pages or balandro.ROW_PAGES) - 1):
        if not following:
            break
        more = fetch_row(following) or []
        following = balandro.next_page(more)
        files += more
    files = [f for f in files if not balandro.is_next(f)]
    cache = load_calidades()
    urls = [(balandro.decode(f.get('file')) or {}).get('url') for f in files]
    urls = [u for u in urls if balandro.needs_page(u)]  # DonTorrent dice la calidad en el nombre
    if check_pages(kind, urls, cache, time.time(), workers):
        save_calidades(cache)
    return files


def check_saved_rows(limit=10):
    """Mira la calidad de los títulos de las filas de Balandro ya guardadas que aún no la tengan (o la tengan vieja),
    hasta limit páginas. Para el servicio: las filas no se quedan vacías esperando a renovarse."""
    cache, now, checked = load_calidades(), time.time(), 0
    for key in sorted(balandro.FILAS):
        entry = load_fila(key) or {}
        kind = balandro.row_kind(entry.get('path') or '')
        if not kind:
            continue
        urls = [u for u in (balandro.page_url(item) for item in entry.get('items') or []) if balandro.needs_page(u)]
        todo = [u for u in urls if u and not calidad.fresh(cache.get(u), now)][:limit - checked]
        checked += check_pages(kind, todo, cache, now)
        if checked >= limit:
            break
    if checked:
        save_calidades(cache)
    return '%d páginas mirando su calidad' % checked if checked else None


def fetch_row(path):
    """La lista tal como la da el addon, con todos los datos que pinta la skin; None si falla (no es una lista
    vacía: filas.keeps distingue las dos)."""
    result = rpc('Files.GetDirectory', {'directory': path, 'media': 'video', 'properties': filas.FIELDS})
    if not result:
        return None
    return result.get('files') or []


def summary(rutas):
    lines = []
    pal = rutas.get('palantir')
    if pal:
        lines.append('Palantir: Películas: %d filas · Series: %d filas' % (
            len(pal.get('peliculas', {})),
            len(pal.get('series', {}))))
    else:
        lines.append('Palantir: no encontrado')
    bg = rutas.get('blackghost')
    if bg:
        names = [discover.DEPORTES['agenda']['label']] if bg.get('agenda') else []
        names += [discover.DEPORTES[k]['label'] for k in menus.ORDEN_DEPORTES if k in bg.get('deportes', {})]
        lines.append('BlackGhost: Deportes: %s' % (', '.join(names) or 'ninguno (¿código de BlackGhost caducado?)'))
    else:
        lines.append('BlackGhost: no encontrado')
    return '\n'.join(lines)


def apply_bg_code():
    """Deja el código del asistente donde BlackGhost lo lee al entrar. Devuelve el código ('' si no hay)."""
    code = setting('bg_codigo').strip()
    if code and read_file(BG_CODE_FILE).strip() != code:
        write_file(BG_CODE_FILE, code)
        log('BlackGhost: código guardado')
    return code


def _discover_blackghost_quietly():
    """BlackGhost buscado desde el servicio: sin preguntar nada y solo si tiene código guardado (si no, al entrar
    abre un teclado). None si no encuentra ninguna fila (código caducado, sin red…)."""
    code = apply_bg_code()
    if not read_file(BG_CODE_FILE).strip():
        return None
    bg = discover.discover_blackghost(list_dir, find_addon, lambda title, labels: -1)
    if not bg or not (bg.get('agenda') or bg.get('deportes')):
        return None
    bg['codigo'] = code
    return bg


def sync_bg_code():
    """El código va dentro de las rutas de BlackGhost: si cambia, se buscan otra vez y se rehace el menú."""
    code = setting('bg_codigo').strip()
    rutas = load_rutas()
    if not code or not rutas or (rutas.get('blackghost') or {}).get('codigo') == code:
        return False
    bg = _discover_blackghost_quietly()
    if not bg:
        log('BlackGhost: con el código nuevo no sale ninguna fila')
        return False
    rutas['blackghost'] = bg
    write_file(RUTAS, json.dumps(rutas, indent=2, ensure_ascii=False))
    set_pending(True)
    log('BlackGhost: filas buscadas con el código nuevo')
    return True


def run_discovery():
    notify('Buscando los menús de Palantir…')
    pal = discover.discover_palantir(list_dir, find_addon, ask)
    notify('Buscando los deportes de BlackGhost…')
    code = apply_bg_code()
    bg = discover.discover_blackghost(list_dir, find_addon, ask)
    if bg and code:
        bg['codigo'] = code
    rutas = {}
    if pal:
        rutas['palantir'] = pal
    if bg:
        rutas['blackghost'] = bg
    write_file(RUTAS, json.dumps(rutas, indent=2, ensure_ascii=False))
    rutas['balandro'] = has_addon(BALANDRO)
    _write_preset(rutas)
    return rutas


def _write_preset(rutas):
    if xbmcvfs.exists(PRESET):
        for name in xbmcvfs.listdir(PRESET)[1]:
            xbmcvfs.delete(PRESET + name)
    menus.write_preset(menus.build_preset(rutas), PRESET, write_file)


def refresh_menu_if_outdated():
    """Si el menú lo montó una versión con otro formato, se deja pendiente para que el servicio lo rehaga. Antes se
    vuelven a buscar las listas de Palantir, que cambian ("Más vistas" pasó a pedir Trakt), y las de BlackGhost si
    tiene código guardado. Lo que no se encuentre se queda como estaba."""
    rutas = load_rutas()
    if not rutas or read_file(MENU_VERSION_FILE).strip() == str(menus.MENU_VERSION):
        return False
    pal = discover.discover_palantir(list_dir, find_addon, lambda title, labels: -1)  # sin preguntar nada
    changed = False
    if pal and (pal.get('peliculas') or pal.get('series')):
        rutas['palantir'], changed = pal, True
    bg = _discover_blackghost_quietly()
    if bg:
        rutas['blackghost'], changed = bg, True
    if changed:
        write_file(RUTAS, json.dumps(rutas, indent=2, ensure_ascii=False))
    set_pending(True)
    return True


# AF3 pone ReloadDone al acabar su rutina de arranque (shortcuts/skinvariables-startup.json).
AF3_STARTED = '!String.IsEmpty(Window(Home).Property(ReloadDone)) + !Window.IsVisible(startup)'


def af3_ready():
    # Ni DefaultConfig.InitDone (las recargas del primer arranque de AF3 pueden borrarlo) ni la ventana de Inicio
    # (AF3 puede arrancar en un hub, como el 11107 de TV): con cualquiera de los dos el menú no llegaba nunca.
    return xbmc.getSkinDir() == SKIN and xbmc.getCondVisibility(AF3_STARTED)


def set_skin(skin_id):
    if xbmc.getSkinDir() != skin_id:
        rpc('Settings.SetSettingValue', {'setting': 'lookandfeel.skin', 'value': skin_id})


def _hub_labels(text):
    try:
        return [h.get('label') for h in json.loads(text or '[]')]
    except ValueError:
        return None


def _wait_for_copy(timeout=15):
    expected = _hub_labels(read_file(PRESET + menus.FILE % 'hubs'))
    monitor = xbmc.Monitor()
    for _ in range(timeout * 2):
        if _hub_labels(read_file(NODES + menus.FILE % 'hubs')) == expected:
            return True
        if monitor.waitForAbort(0.5):
            break
    log('copy_menufolder no terminó a tiempo')
    return False


def apply_skin_config():
    """Aplica el preset. Devuelve False si skinvariables no llegó a copiar el menú."""
    now = time.strftime('%Y-%m-%d_%H:%M:%S')
    first_run = not xbmc.getCondVisibility('Skin.HasSetting(DefaultConfig.InitDone)')
    rutas = load_rutas()
    if rutas:  # se rehace con el formato de esta versión; sin rutas guardadas no se toca el que haya
        _write_preset(rutas)
    copied = True
    for builtin in menus.skin_builtins(rutas, PRESET, now, first_run):
        xbmc.executebuiltin(builtin, True)
        if 'copy_menufolder' in builtin:
            copied = _wait_for_copy()
    xbmc.executebuiltin('Dialog.Close(1130,true)')
    if copied and rutas:
        write_file(MENU_VERSION_FILE, str(menus.MENU_VERSION))
    return copied


def finish_pending(wait=lambda: False):
    """Monta el menú que dejó pendiente el asistente en cuanto AF3 ha arrancado.
    True = montado, False = falló la copia (sigue pendiente), None = nada que hacer todavía.
    wait() deja que la skin termine de asentarse y devuelve True si Kodi se está cerrando."""
    if not (pending() and af3_ready()) or wait():
        return None
    if not apply_skin_config():
        return False
    set_pending(False)
    notify('Menú de papá listo')
    return True


def pending():
    return xbmcvfs.exists(PENDING)


def set_pending(flag):
    if flag:
        write_file(PENDING, '1')
    elif xbmcvfs.exists(PENDING):
        xbmcvfs.delete(PENDING)


# --- arreglos a otros addons -------------------------------------------------

# (addon, archivo dentro del addon, arreglo, ¿lo necesita esta versión?)
PATCHES = [
    (YOUTUBE, patches.YOUTUBE_FILE, patches.patch_youtube, patches.youtube_needs_patch),
    (SKIN, patches.AF3_FILE, patches.patch_af3_rows, lambda version: True),
    (SKIN, patches.AF3_HOME_FILE, patches.patch_af3_search, lambda version: True),
    (SKIN, patches.AF3_STRINGS_FILE, patches.patch_af3_strings, lambda version: True),
    (SKIN, patches.AF3_IMAGES_FILE, patches.patch_af3_episode_thumbs, lambda version: True),
    (SKINVARIABLES, patches.SKINVARIABLES_STRINGS_FILE, patches.patch_skinvariables_strings, lambda version: True),
    (BALANDRO, patches.BALANDRO_FILE, patches.patch_balandro_quality, lambda version: True),
    (BALANDRO, patches.DONTORRENTS_FILE, patches.patch_dontorrents_search, lambda version: True),
    (TELEGRAM_ADDON, patches.TELEGRAM_FILE, patches.patch_telegram_topic, lambda version: True),
]


def apply_patches():
    """Aplica los arreglos de patches.py que falten (tras instalar o actualizar YouTube o la skin) y guarda
    antes el original en addon_data/script.papa.inicio/backup/. Devuelve los addons tocados."""
    done = []
    for addon_id, rel, patch, wanted in PATCHES:
        version = addon_version(addon_id) if has_addon(addon_id) else ''
        if not version or not wanted(version):
            continue
        path = 'special://home/addons/%s/%s' % (addon_id, rel)
        text = read_file(path)
        new = patch(text) if text else None
        if not new:
            continue
        backup = BACKUP + '%s-%s-%s.orig' % (addon_id, version, rel.rsplit('/', 1)[-1])
        if not xbmcvfs.exists(backup):
            write_file(backup, text)
        write_file(path, new)
        log('arreglo aplicado a %s %s' % (addon_id, version))
        done.append(addon_id)
    return done


# --- catálogo del grupo de Telegram ------------------------------------------------------------------------------

def _tmdb_search(key):
    from urllib.parse import urlencode

    def search(kind, query, year):
        params = {'api_key': key, 'language': 'es-ES', 'include_adult': 'false', 'query': query}
        if year:
            params['year' if kind == 'movie' else 'first_air_date_year'] = year
        text = fetch_text('https://api.themoviedb.org/3/search/%s?%s' % (kind, urlencode(params)))
        try:
            return (json.loads(text) if text else {}).get('results', [])[:10]
        except ValueError:
            return []
    return search


def _head_bytes(url, size=64 * 1024):
    from urllib.request import Request, urlopen
    try:
        with urlopen(Request(url, headers={'Range': 'bytes=0-%d' % (size - 1)}), timeout=60) as r:
            return r.read(size)
    except Exception as exc:
        log('Telegram cabecera: %s' % type(exc).__name__)
        return b''


def telegram_update(force=False):
    """Añade al catálogo (telegram.db) lo subido al grupo desde la última vez: una vez al día, de madrugada (o ya,
    con force). Devuelve un resumen, o None si no tocaba o falta algo (catálogo, sesión de Telegram, clave TMDb)."""
    import sqlite3
    from resources.lib import telegram, telegram_idx
    path = xbmcvfs.translatePath(TELEGRAM)
    if not xbmcvfs.exists(TELEGRAM):
        return None
    db = sqlite3.connect(path)
    try:
        row = db.execute("SELECT valor FROM estado WHERE clave = 'actualizado'").fetchone()
        if not force and not telegram.due(time.localtime(), row[0] if row else ''):
            return None
        token, peer, key = read_file(telegram.TOKEN).strip(), telegram.peer(path), setting('tmdb_key')
        if not (token and peer and key):
            return None
        since = telegram_idx.last_msg(db)
        items = telegram.new_videos(lambda url: json.loads(fetch_text(url) or '{}'), telegram.base(token), peer, since)
        temas = telegram_idx.topics(db)
        rows = [telegram_idx.from_addon(i, temas) for i in items]
        videos = telegram_idx.with_headers(rows)  # cada vídeo con lo que dice su carátula
        for v in videos:  # la resolución que Telegram no dice (.mkv, .avi), de los primeros 64 KB
            if v.get('tema') in ('Películas', 'Series') and not (v.get('width') and v.get('height')):
                found = telegram_idx.probe_resolution(_head_bytes(telegram.stream_url(telegram.base(token), peer, v['id'])))
                if found:
                    v['width'], v['height'] = found
        found = telegram_idx.catalogue(videos, _tmdb_search(key))
        telegram_idx.store(db, found, max([since] + [r['id'] for r in rows]), peer)
        db.execute("INSERT OR REPLACE INTO estado VALUES ('actualizado', ?)", (time.strftime('%Y-%m-%d'),))
        db.commit()
    finally:
        db.close()
    summary = '%d vídeos nuevos: %d de películas y %d capítulos con ficha' % (
        len(videos), len(found['pelis']), len(found['capitulos']))
    log('Telegram: ' + summary)
    return summary


# --- lo de las filas, preparado de antemano en AllDebrid (precalentar.py) ----------------------------------------

PRECALENTADO = PROFILE + 'precalentado.json'


def _json_get(url):
    text = fetch_text(url)
    try:
        return json.loads(text) if text else {}
    except ValueError:
        return {}


def _alldebrid_api():
    """(net, cabeceras, url de la API) de AllDebrid con la cuenta vinculada en ResolveURL, o None."""
    try:
        from resolveurl.plugins import alldebrid
        resolver = alldebrid.AllDebridResolver()
    except Exception as exc:
        log('AllDebrid no disponible: %s' % exc)
        return None
    if resolver.get_setting('enabled') != 'true' or not resolver.get_setting('token'):
        return None
    return resolver.net, resolver.headers, alldebrid.api_url


def _row_tmdbs(key, kind):
    from resources.lib import telegram
    items = balandro.fila(key, (load_fila(key) or {}).get('items') or []) if key in balandro.FILAS else []
    ids = [str((i.get('uniqueids') or {}).get('tmdb') or '') for i in items]
    year = time.localtime().tm_year
    since = year - 1 if key == 'peliculas.estrenos' else None
    ids += [str(r['id']) for r in telegram.newest(xbmcvfs.translatePath(TELEGRAM), kind, since=since)]
    return [i for i in ids if i.isdigit()]


def prewarm(force=False):
    """Pide a AllDebrid el mejor torrent en castellano de lo que sale en las filas (precalentar.py) y quita de la
    lista lo pedido hace más de dos semanas. Devuelve un resumen, o None si falta AllDebrid o la clave de TMDb."""
    from resources.lib import debrid, precalentar, torrentio
    api, key = _alldebrid_api(), setting('tmdb_key')
    if not api or not key:
        return None
    net, headers, url = api
    now = time.time()
    try:
        record = json.loads(read_file(PRECALENTADO) or '{}')
    except ValueError:
        record = {}
    shows = []
    for tmdb in _row_tmdbs('series.novedades', 'series')[:precalentar.MAX_PER_NIGHT]:
        last = precalentar.last_episode(_json_get('https://api.themoviedb.org/3/tv/%s?api_key=%s' % (tmdb, key)))
        if last:
            shows.append((tmdb, last[0], last[1]))
    movies = _row_tmdbs('peliculas.estrenos', 'peliculas') + _row_tmdbs('peliculas.recientes', 'peliculas')
    asked = ready = downloading = 0
    for target in precalentar.targets(movies, shows):
        if not force and not precalentar.due(record, target, now):
            continue
        kind, tmdb, season, episode = target
        path = 'tv' if kind == 'series' else 'movie'
        imdb = _json_get('https://api.themoviedb.org/3/%s/%s/external_ids?api_key=%s' % (path, tmdb, key)).get('imdb_id')
        found = torrentio.best(_json_get(torrentio.stream_url(kind, imdb, season, episode)).get('streams')) if imdb else []
        record[precalentar.key(target)] = {'time': now, 'id': None}
        if not found:
            continue
        asked += 1
        try:
            answer = json.loads(net.http_POST(url + '/magnet/upload', form_data={'magnets': debrid.magnet(
                found[0]['btih'], found[0]['title'])}, headers=headers).content)
            magnet = ((answer.get('data') or {}).get('magnets') or [{}])[0]
        except Exception as exc:
            log('AllDebrid preparar %s: %s' % (tmdb, exc))
            continue
        if magnet.get('ready'):  # ya lo tenía: arrancará al momento; no se deja en la lista
            ready += 1
            _alldebrid_delete(net, headers, url, magnet.get('id'))
        else:
            downloading += 1
            record[precalentar.key(target)]['id'] = magnet.get('id')
    old = precalentar.to_delete(record, now)
    for magnet_id in old:
        _alldebrid_delete(net, headers, url, magnet_id)
    write_file(PRECALENTADO, json.dumps(precalentar.forget(record, old)))
    summary = '%d pedidos a AllDebrid: %d ya listos, %d descargándose; %d quitados de la lista' % (
        asked, ready, downloading, len(old))
    log('Precalentar: ' + summary)
    return summary


def _alldebrid_delete(net, headers, url, magnet_id):
    if not magnet_id:
        return
    try:
        net.http_POST(url + '/magnet/delete', form_data={'id': magnet_id}, headers=headers)
    except Exception as exc:
        log('AllDebrid quitar %s: %s' % (magnet_id, exc))


NOCHE = PROFILE + 'noche.json'


def nightly():
    """Lo de cada madrugada (una vez al día, con la caja sin usar): lo nuevo del grupo de Telegram al catálogo y lo
    de las filas preparado en AllDebrid."""
    from resources.lib import telegram
    try:
        last = json.loads(read_file(NOCHE) or '{}').get('dia', '')
    except ValueError:
        last = ''
    if not telegram.due(time.localtime(), last):
        return None
    write_file(NOCHE, json.dumps({'dia': time.strftime('%Y-%m-%d')}))
    out = []
    for name, job in (('Telegram', lambda: telegram_update(force=True)), ('AllDebrid', prewarm)):
        try:
            out.append('%s: %s' % (name, job()))
        except Exception as exc:
            log('%s de madrugada: %s' % (name, exc))
    return ' · '.join(out)


# --- diagnóstico ------------------------------------------------------------

def report_destinations(storage_dirs):
    usb = ['/storage/%s/' % d for d in storage_dirs if d not in ('emulated', 'self')]
    return usb + ['/storage/emulated/0/Download/']


def _tree(root, depth=2, limit=30):
    rows = []

    def walk(path, level):
        for e in list_dir(path)[:limit]:
            rows.append((level, discover.clean(e['label']), e['file']))
            if e['filetype'] == 'directory' and level + 1 < depth and diagnostico.should_walk(e['label']):
                walk(e['file'], level + 1)

    walk(root, 0)
    return rows


def _addon_texts(addon_id, exts=('.py', '.xml', '.txt', '.json', '.md'), max_files=400):
    stack, texts = ['special://home/addons/%s/' % addon_id], []
    while stack and len(texts) < max_files:
        folder = stack.pop()
        dirs, files = xbmcvfs.listdir(folder)
        stack += [folder + d + '/' for d in dirs]
        texts += [read_file(folder + f) for f in files if f.lower().endswith(exts)]
    return '\n'.join(texts)


def run_diagnostico():
    notify('Preparando el informe… puede tardar un minuto')
    pal = find_addon(['palantir'])
    bg = find_addon(['black ghost', 'blackghost'])
    ids = [SKIN, TMDBH, 'script.skinvariables', YOUTUBE, pal, bg]
    info = {
        'kodi': xbmc.getInfoLabel('System.BuildVersion'),
        'skin': xbmc.getSkinDir(),
        'addons': {i: addon_version(i) for i in ids if has_addon(i)},
        'trees': {}, 'telegram': [], 'bg_setting_ids': [],
        'rutas': load_rutas(),
        'keys_present': {'TMDb': bool(setting('tmdb_key')), 'OMDb': bool(setting('omdb_key'))},
    }
    if pal:
        info['trees']['Palantir'] = _tree('plugin://%s/' % pal)
    if bg:
        info['trees']['BlackGhost'] = _tree('plugin://%s/' % bg)
        info['telegram'] = diagnostico.find_telegram_links(_addon_texts(bg))
        info['bg_setting_ids'] = diagnostico.setting_ids(
            read_file('special://home/addons/%s/resources/settings.xml' % bg))
    text = diagnostico.build_report(info)
    write_file(PROFILE + INFORME, text)
    saved = []
    try:
        storage = xbmcvfs.listdir('/storage/')[0]
    except Exception:
        storage = []
    for dest in report_destinations(storage):
        try:
            if xbmcvfs.exists(dest):
                write_file(dest + INFORME, text)
                if xbmcvfs.exists(dest + INFORME):
                    saved.append(dest + INFORME)
        except Exception as exc:
            log('no se pudo guardar en %s: %s' % (dest, exc))
    where = '\n'.join(saved) or xbmcvfs.translatePath(PROFILE + INFORME)
    xbmcgui.Dialog().textviewer('Informe guardado en: %s' % where.replace('\n', ' · '), text)
    return text
