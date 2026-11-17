# -*- coding: utf-8 -*-
"""Todo lo que toca Kodi: JSON-RPC, diálogos, archivos, skin y ajustes de otros addons."""
import json
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import diagnostico, discover, menus, patches

ADDON_ID = 'script.papa.inicio'
TITLE = 'Kodi de Papá'
SKIN = menus.SKIN
YOUTUBE = 'plugin.video.youtube'
TMDBH = 'plugin.video.themoviedb.helper'
TMDBH_ES_ES = 20  # índice de es-ES en LANGUAGES de TMDb Helper
PROFILE = 'special://profile/addon_data/%s/' % ADDON_ID
PRESET = PROFILE + 'preset/'
RUTAS = PROFILE + 'rutas.json'
PENDING = PROFILE + 'pendiente'
BACKUP = PROFILE + 'backup/'
MENU_VERSION_FILE = PROFILE + 'menu_version'
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
    xbmcvfs.mkdirs(path.rsplit('/', 1)[0] + '/')
    f = xbmcvfs.File(path, 'w')
    try:
        f.write(bytearray(text.encode('utf-8')))
    finally:
        f.close()


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
]


def ask_keys():
    dialog = xbmcgui.Dialog()
    for sid, heading in KEYS:
        value = dialog.input(heading, defaultt=setting(sid))
        if value and value.strip():
            set_setting(sid, value.strip())


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
    omdb = setting('omdb_key')
    if omdb:
        helper.setSetting('omdb_apikey', omdb)
    return True


# --- menús ------------------------------------------------------------------

def load_rutas():
    try:
        return json.loads(read_file(RUTAS) or '{}')
    except ValueError:
        return {}


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
        lines.append('BlackGhost: Deportes: %s' % (', '.join(names) or 'ninguno'))
    else:
        lines.append('BlackGhost: no encontrado')
    return '\n'.join(lines)


def run_discovery():
    notify('Buscando los menús de Palantir…')
    pal = discover.discover_palantir(list_dir, find_addon, ask)
    notify('Buscando los deportes de BlackGhost…')
    bg = discover.discover_blackghost(list_dir, find_addon, ask)
    rutas = {}
    if pal:
        rutas['palantir'] = pal
    if bg:
        rutas['blackghost'] = bg
    write_file(RUTAS, json.dumps(rutas, indent=2, ensure_ascii=False))
    _write_preset(rutas)
    return rutas


def _write_preset(rutas):
    if xbmcvfs.exists(PRESET):
        for name in xbmcvfs.listdir(PRESET)[1]:
            xbmcvfs.delete(PRESET + name)
    menus.write_preset(menus.build_preset(rutas), PRESET, write_file)


def refresh_menu_if_outdated():
    """Si el menú lo montó una versión con otro formato, se deja pendiente para que el servicio lo rehaga. Antes se
    vuelven a buscar las listas de Palantir, que cambian ("Más vistas" pasó a pedir Trakt); BlackGhost no se toca."""
    rutas = load_rutas()
    if not rutas or read_file(MENU_VERSION_FILE).strip() == str(menus.MENU_VERSION):
        return False
    pal = discover.discover_palantir(list_dir, find_addon, lambda title, labels: -1)  # sin preguntar nada
    if pal and (pal.get('peliculas') or pal.get('series')):
        rutas['palantir'] = pal
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
