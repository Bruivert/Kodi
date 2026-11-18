import json
import os
import py_compile
import xml.etree.ElementTree as ET

from resources.lib import kodi_setup as ks

ADDON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'script.papa.inicio')

ADDONS = [
    {'addonid': 'plugin.video.palantirviejo', 'name': 'Palantir viejo', 'enabled': False},
    {'addonid': 'plugin.video.palantir3', 'name': '[COLOR blue]Palantir 3[/COLOR]', 'enabled': True},
    {'addonid': 'plugin.video.bgh', 'name': '[B]Black Ghost[/B]', 'enabled': True},
    {'addonid': 'plugin.video.blackghost.sports', 'name': 'BG', 'enabled': True},
]


def test_match_addon_prefers_enabled_and_reads_names_with_markup():
    assert ks.match_addon(ADDONS, ['palantir']) == 'plugin.video.palantir3'
    assert ks.match_addon(ADDONS, ['black ghost', 'blackghost']) == 'plugin.video.bgh'
    assert ks.match_addon(ADDONS[3:], ['black ghost', 'blackghost']) == 'plugin.video.blackghost.sports'
    assert ks.match_addon(ADDONS, ['nada']) is None


def test_report_destinations_include_usb_drives_and_downloads():
    dests = ks.report_destinations(['emulated', 'self', '1A2B-3C4D', 'sdcard0'])
    assert dests == ['/storage/1A2B-3C4D/', '/storage/sdcard0/', '/storage/emulated/0/Download/']


def test_addon_xml_declares_script_and_service_for_omega():
    root = ET.parse(os.path.join(ADDON_DIR, 'addon.xml')).getroot()
    assert root.get('id') == 'script.papa.inicio'
    points = {e.get('point'): e.get('library') for e in root.iter('extension')}
    assert points['xbmc.python.script'] == 'default.py'
    assert points['xbmc.service'] == 'service.py'
    imports = {i.get('addon'): i.get('version') for i in root.iter('import')}
    assert imports == {'xbmc.python': '3.0.1', 'script.module.requests': '2.22.0'}


def test_settings_have_keys_and_trailer_switch():
    root = ET.parse(os.path.join(ADDON_DIR, 'resources', 'settings.xml')).getroot()
    ids = {s.get('id') for s in root.iter('setting')}
    assert {'tmdb_key', 'omdb_key', 'trailers_auto', 'bg_codigo'} <= ids


def test_addon_lists_favourites_as_a_video_plugin():
    root = ET.parse(os.path.join(ADDON_DIR, 'addon.xml')).getroot()
    plugin = [e for e in root.iter('extension') if e.get('point') == 'xbmc.python.pluginsource']
    assert len(plugin) == 1 and plugin[0].get('library') == 'plugin.py'
    assert plugin[0].find('provides').text == 'video'


def test_entry_points_compile():
    for name in ('default.py', 'service.py', 'plugin.py'):
        py_compile.compile(os.path.join(ADDON_DIR, name), doraise=True)


def test_summary_counts_rows_and_names_sports():
    rutas = {'palantir': {'peliculas': {'estrenos': {}, 'populares': {}, 'valoradas': {}, 'generos': {}},
                          'series': {'novedades': {}, 'emision': {}}},
             'blackghost': {'agenda': {'path': 'x'}, 'deportes': {'futbol': {}, 'ufc': {}, 'padel': {}}}}
    text = ks.summary(rutas)
    assert 'Películas: 4 filas' in text and 'Series: 2 filas' in text
    assert 'Deportes: Agenda de hoy, Fútbol, UFC y boxeo' in text


def test_summary_when_addons_missing():
    text = ks.summary({})
    assert 'Palantir: no encontrado' in text and 'BlackGhost: no encontrado' in text


# Condiciones de Kodi que simulamos. Si el código pregunta otra (por ejemplo Window.IsVisible(home)), KeyError.
CONDITIONS = {
    'String.IsEmpty(Window(Home).Property(ReloadDone))': lambda s: not s.get('reload_done'),
    'Window.IsVisible(startup)': lambda s: s.get('startup', False),
    'Skin.HasSetting(DefaultConfig.InitDone)': lambda s: s.get('initdone', False),
}

# Como estaba la caja: AF3 arrancada en el hub de TV (11107) y sin DefaultConfig.InitDone.
CAJA = {'reload_done': True, 'startup': False, 'initdone': False}


def fake_kodi(monkeypatch, skin, state):
    def cond(expr):
        atoms = [a.strip() for a in expr.split('+')]
        return all(CONDITIONS[a.lstrip('!')](state) != a.startswith('!') for a in atoms)
    monkeypatch.setattr(ks.xbmc, 'getSkinDir', lambda: skin)
    monkeypatch.setattr(ks.xbmc, 'getCondVisibility', cond)


def test_af3_ready_once_its_startup_finished_even_without_initdone(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, CAJA)
    assert ks.af3_ready()
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, startup=True))
    assert not ks.af3_ready()
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, reload_done=False))
    assert not ks.af3_ready()
    fake_kodi(monkeypatch, 'skin.estuary', CAJA)
    assert not ks.af3_ready()


def fake_apply(monkeypatch, copied=True):
    ran = []
    monkeypatch.setattr(ks.xbmc, 'executebuiltin', lambda b, wait=False: ran.append(b))
    monkeypatch.setattr(ks, 'load_rutas', lambda: {})
    monkeypatch.setattr(ks, '_wait_for_copy', lambda: copied)
    return ran


def test_apply_finishes_af3_first_run_when_initdone_was_lost(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, CAJA)
    ran = fake_apply(monkeypatch)
    assert ks.apply_skin_config()
    assert 'Skin.SetBool(DefaultConfig.InitDone)' in ran
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, initdone=True))
    ran = fake_apply(monkeypatch)
    ks.apply_skin_config()
    assert 'Skin.SetBool(DefaultConfig.InitDone)' not in ran


def fake_pending(monkeypatch):
    flags = []
    monkeypatch.setattr(ks, 'pending', lambda: True)
    monkeypatch.setattr(ks, 'set_pending', flags.append)
    monkeypatch.setattr(ks, 'notify', lambda msg: None)
    return flags


def test_finish_pending_applies_menu_from_any_af3_window(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, CAJA)
    fake_apply(monkeypatch)
    flags = fake_pending(monkeypatch)
    assert ks.finish_pending()
    assert flags == [False]


def test_finish_pending_keeps_flag_when_copy_failed(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, CAJA)
    fake_apply(monkeypatch, copied=False)
    flags = fake_pending(monkeypatch)
    assert ks.finish_pending() is False  # falló: el servicio cuenta el intento
    assert flags == []


def test_finish_pending_waits_for_af3(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, startup=True))
    ran = fake_apply(monkeypatch)
    flags = fake_pending(monkeypatch)
    assert ks.finish_pending() is None  # nada que hacer todavía
    assert ran == [] and flags == []
    fake_kodi(monkeypatch, ks.SKIN, CAJA)
    assert ks.finish_pending(wait=lambda: True) is None  # Kodi se cierra durante la espera
    assert ran == [] and flags == []


def test_service_starts_even_without_requests_module(monkeypatch):
    import importlib
    import sys
    monkeypatch.setitem(sys.modules, 'requests', None)  # import requests -> ImportError
    sys.modules.pop('service', None)
    service = importlib.import_module('service')
    assert callable(service.http_get)


from resources.lib import patches as pt  # noqa: E402
from tests.test_patches import AF3, YOUTUBE  # noqa: E402

YT_PATH = 'special://home/addons/plugin.video.youtube/' + pt.YOUTUBE_FILE
AF3_PATH = 'special://home/addons/skin.arctic.fuse.3/' + pt.AF3_FILE


def fake_addons(monkeypatch, files, versions):
    written = {}
    monkeypatch.setattr(ks, 'has_addon', lambda a: a in versions)
    monkeypatch.setattr(ks, 'addon_version', lambda a: versions.get(a, ''))
    monkeypatch.setattr(ks, 'read_file', lambda p: written.get(p, files.get(p, '')))
    monkeypatch.setattr(ks, 'write_file', lambda p, t: written.__setitem__(p, t))
    monkeypatch.setattr(ks.xbmcvfs, 'exists', lambda p: p in files or p in written)
    monkeypatch.setattr(ks, 'log', lambda msg: None)
    return written


def test_apply_patches_fixes_youtube_and_skin_keeping_the_originals(monkeypatch):
    files = {YT_PATH: YOUTUBE, AF3_PATH: AF3}
    written = fake_addons(monkeypatch, files, {'plugin.video.youtube': '7.4.4', 'skin.arctic.fuse.3': '3.5.2'})
    assert ks.apply_patches() == ['plugin.video.youtube', 'skin.arctic.fuse.3']
    assert written[YT_PATH] == pt.patch_youtube(YOUTUBE)
    assert written[AF3_PATH] == pt.patch_af3_rows(AF3)
    backups = {p: t for p, t in written.items() if p.startswith(ks.BACKUP)}
    assert sorted(backups.values()) == sorted([YOUTUBE, AF3])
    assert any('plugin.video.youtube-7.4.4' in p for p in backups)
    assert ks.apply_patches() == []  # ya aplicados: no se toca nada más


def test_apply_patches_leaves_fixed_youtube_versions_and_missing_addons_alone(monkeypatch):
    written = fake_addons(monkeypatch, {YT_PATH: YOUTUBE}, {'plugin.video.youtube': '7.4.5'})
    assert ks.apply_patches() == []
    assert written == {}



def fresh_service(monkeypatch, http, post=lambda url, payload: {}):
    import importlib
    import sys
    sys.modules.pop('service', None)
    service = importlib.import_module('service')
    monkeypatch.setattr(service.ks, 'setting', lambda sid: 'clave')
    monkeypatch.setattr(service.ks, 'has_addon', lambda a: True)
    monkeypatch.setattr(service, 'http_get', http)
    monkeypatch.setattr(service, 'http_post', post)
    return service


SPAIN = {'results': [{'site': 'YouTube', 'type': 'Trailer', 'iso_639_1': 'es', 'iso_3166_1': 'ES', 'key': 'abc'}]}


def test_trailer_lookup_is_retried_after_a_network_failure(monkeypatch):
    calls = []

    def flaky(url):
        calls.append(url)
        if len(calls) == 1:
            raise OSError('sin red')  # la Wi-Fi aún no ha arrancado
        return SPAIN
    resolver = fresh_service(monkeypatch, flaky).Resolver()
    assert resolver('movie', '603', '', 'Matrix', '1999') is None
    assert resolver('movie', '603', '', 'Matrix', '1999') == 'abc'
    asked = len(calls)
    assert resolver('movie', '603', '', 'Matrix', '1999') == 'abc'
    assert len(calls) == asked  # lo bueno sí se guarda


def test_movie_without_spain_trailer_is_not_asked_again(monkeypatch):
    calls = []

    def none(url):
        calls.append(url)
        return {'results': []}
    resolver = fresh_service(monkeypatch, none).Resolver()
    assert resolver('movie', '603', '', 'Matrix', '1999') is None
    asked = len(calls)
    assert resolver('movie', '603', '', 'Matrix', '1999') is None
    assert len(calls) == asked


def test_youtube_search_is_retried_after_a_network_failure(monkeypatch):
    from tests.test_trailers import yt_answer
    searches = []

    def tmdb(url):
        return {'title': 'Allen', 'release_date': '2026-11-12'} if '/movie/603?' in url else {'results': []}

    def youtube(url, payload):
        searches.append(payload['query'])
        if len(searches) == 1:
            raise OSError('sin red')
        return yt_answer(('allen', 'Allen - Tráiler español', 'CineTrailer', '2:24'))
    resolver = fresh_service(monkeypatch, tmdb, youtube).Resolver()
    assert resolver('movie', '603', '', 'Allen', '2026') is None
    assert resolver('movie', '603', '', 'Allen', '2026') == 'allen'
    assert resolver('movie', '603', '', 'Allen', '2026') == 'allen'
    assert searches == ['Allen 2026 tráiler español'] * 2


class FakeAddon(object):
    def __init__(self, values):
        self.values = values

    def getSetting(self, sid):
        return self.values.get(sid, '')

    def setSetting(self, sid, value):
        self.values[sid] = value


def fake_youtube(monkeypatch, values, installed=True):
    monkeypatch.setattr(ks, 'has_addon', lambda a: installed and a == ks.YOUTUBE)
    monkeypatch.setattr(ks.xbmcaddon, 'Addon', lambda addon_id=None: FakeAddon(values))
    monkeypatch.setattr(ks, 'log', lambda msg: None)


def test_youtube_is_set_to_spain_spanish_so_it_never_picks_the_english_auto_dub(monkeypatch):
    # En la caja YouTube venía en en-US y "La bola negra" sonaba con el doblaje automático en inglés.
    values = {'youtube.language': 'en-US', 'youtube.region': 'US', 'youtube.http.stream_redirect': 'false'}
    fake_youtube(monkeypatch, values)
    assert ks.apply_youtube_settings()
    assert values['youtube.language'] == 'es' and values['youtube.region'] == 'ES'
    assert not ks.apply_youtube_settings()  # ya estaba


def test_youtube_sends_video_straight_from_google_so_stopping_a_trailer_is_instant(monkeypatch):
    # Pasando el vídeo por su servidor interno, parar un tráiler dejaba a Kodi 20 s esperando una descarga.
    values = {'youtube.language': 'es', 'youtube.region': 'ES', 'youtube.http.stream_redirect': 'false'}
    fake_youtube(monkeypatch, values)
    assert ks.apply_youtube_settings()
    assert values['youtube.http.stream_redirect'] == 'true'


def test_youtube_settings_leave_a_ready_or_missing_addon_alone(monkeypatch):
    values = {'youtube.language': 'es', 'youtube.region': 'ES', 'youtube.http.stream_redirect': 'true'}
    fake_youtube(monkeypatch, values)
    assert not ks.apply_youtube_settings()
    fake_youtube(monkeypatch, {}, installed=False)
    assert not ks.apply_youtube_settings()



def fake_menu_files(monkeypatch, files):
    written = {}
    monkeypatch.setattr(ks, 'read_file', lambda p: written.get(p, files.get(p, '')))
    monkeypatch.setattr(ks, 'write_file', lambda p, t: written.__setitem__(p, t))
    monkeypatch.setattr(ks.xbmcvfs, 'exists', lambda p: p in files or p in written)
    monkeypatch.setattr(ks.xbmcvfs, 'listdir', lambda p: ([], []))
    flags = []
    monkeypatch.setattr(ks, 'set_pending', flags.append)
    return written, flags


RUTAS_JSON = '{"palantir": {"peliculas": {"estrenos": {"label": "Estrenos", "path": "plugin://p/estrenos"}}}}'


def fake_palantir(monkeypatch, tree):
    from tests.test_discover import find_addon
    monkeypatch.setattr(ks, 'list_dir', lambda path: tree.get(path, []))
    monkeypatch.setattr(ks, 'find_addon', find_addon)


def test_menu_made_by_an_older_version_is_applied_again(monkeypatch):
    written, flags = fake_menu_files(monkeypatch, {ks.RUTAS: RUTAS_JSON, ks.MENU_VERSION_FILE: '1'})
    fake_palantir(monkeypatch, {})  # Palantir no contesta: se rehace con las rutas guardadas
    assert ks.refresh_menu_if_outdated()
    assert flags == [True]  # el servicio lo vuelve a montar al arrancar
    assert ks.RUTAS not in written


OLD_RUTAS = {'palantir': {'id': 'plugin.video.palantir3',
                          'peliculas': {'populares': {'label': 'Más vistas', 'path': 'plugin://p/mas-vistas'}}},
             'blackghost': {'id': 'plugin.video.blackghost', 'agenda': {'label': 'Agenda', 'path': 'plugin://bg/a'}}}


def test_older_menu_looks_for_palantir_lists_again(monkeypatch):
    # Palantir cambia: "Más vistas" ahora pide Trakt. Al actualizar, el servicio vuelve a buscar sus listas.
    from tests.test_discover import REAL_TREE
    written, flags = fake_menu_files(monkeypatch, {ks.RUTAS: json.dumps(OLD_RUTAS), ks.MENU_VERSION_FILE: '2'})
    fake_palantir(monkeypatch, REAL_TREE)
    assert ks.refresh_menu_if_outdated()
    rutas = json.loads(written[ks.RUTAS])
    assert rutas['palantir']['peliculas']['recientes']['label'] == 'Últimas añadidas'
    assert 'populares' not in rutas['palantir']['peliculas']
    assert rutas['blackghost'] == OLD_RUTAS['blackghost']  # lo demás no se toca
    assert flags == [True]


def test_menu_up_to_date_or_never_made_is_left_alone(monkeypatch):
    from resources.lib import menus
    written, flags = fake_menu_files(monkeypatch, {ks.RUTAS: RUTAS_JSON, ks.MENU_VERSION_FILE: str(menus.MENU_VERSION)})
    assert not ks.refresh_menu_if_outdated()
    written, flags = fake_menu_files(monkeypatch, {})  # el asistente aún no se ha usado
    assert not ks.refresh_menu_if_outdated()
    assert flags == []


def test_apply_rebuilds_the_preset_from_saved_rutas_and_records_the_version(monkeypatch):
    from resources.lib import menus
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, initdone=True))
    monkeypatch.setattr(ks.xbmc, 'executebuiltin', lambda b, wait=False: None)
    monkeypatch.setattr(ks, '_wait_for_copy', lambda: True)
    written, _ = fake_menu_files(monkeypatch, {ks.RUTAS: RUTAS_JSON})
    assert ks.apply_skin_config()
    rows = json.loads(written[ks.PRESET + menus.FILE % '1101widgets'])
    assert rows[0]['widget_sortby'] == 'track'
    assert written[ks.MENU_VERSION_FILE] == str(menus.MENU_VERSION)


def test_apply_never_overwrites_the_preset_without_saved_rutas(monkeypatch):
    fake_kodi(monkeypatch, ks.SKIN, dict(CAJA, initdone=True))
    monkeypatch.setattr(ks.xbmc, 'executebuiltin', lambda b, wait=False: None)
    monkeypatch.setattr(ks, '_wait_for_copy', lambda: True)
    written, _ = fake_menu_files(monkeypatch, {})
    ks.apply_skin_config()
    assert not [p for p in written if p.startswith(ks.PRESET)]


# --- Código de BlackGhost: va dentro de sus rutas y caduca cada cierto tiempo ---

def fake_bg(monkeypatch, files, code):
    from tests.test_discover import TREE, find_addon
    written, flags = fake_menu_files(monkeypatch, files)
    monkeypatch.setattr(ks, 'setting', lambda sid: code if sid == 'bg_codigo' else '')
    listed = []

    def list_dir(path):
        listed.append(path)
        return TREE.get(path, []) if written.get(ks.BG_CODE_FILE, files.get(ks.BG_CODE_FILE)) == 'n17' else []
    monkeypatch.setattr(ks, 'list_dir', list_dir)
    monkeypatch.setattr(ks, 'find_addon', find_addon)
    return written, flags, listed


BG_RUTAS = json.dumps({'palantir': {'peliculas': {'estrenos': {'label': 'E', 'path': 'plugin://p/e'}}},
                       'blackghost': {'id': 'plugin.video.blackghost', 'codigo': 'n16',
                                      'agenda': {'label': 'Agenda', 'path': 'plugin://bg/?n16'}}})


def test_new_blackghost_code_is_saved_for_blackghost_and_the_rows_are_found_again(monkeypatch):
    written, flags, _ = fake_bg(monkeypatch, {ks.RUTAS: BG_RUTAS}, 'n17')
    assert ks.sync_bg_code()
    assert written[ks.BG_CODE_FILE] == 'n17'  # BlackGhost entra sin preguntarlo
    bg = json.loads(written[ks.RUTAS])['blackghost']
    assert bg['codigo'] == 'n17' and bg['agenda']['path'].endswith('?dplus')
    assert json.loads(written[ks.RUTAS])['palantir'] == json.loads(BG_RUTAS)['palantir']
    assert flags == [True]  # el servicio rehace el menú


def test_same_or_empty_code_changes_nothing(monkeypatch):
    rutas = BG_RUTAS.replace('"n16"', '"n17"')
    written, flags, listed = fake_bg(monkeypatch, {ks.RUTAS: rutas, ks.BG_CODE_FILE: 'n17'}, 'n17')
    assert not ks.sync_bg_code() and written == {} and flags == [] and listed == []
    written, flags, listed = fake_bg(monkeypatch, {ks.RUTAS: BG_RUTAS}, '')
    assert not ks.sync_bg_code() and written == {} and flags == [] and listed == []


def test_code_rejected_by_blackghost_keeps_the_old_rows(monkeypatch):
    written, flags, _ = fake_bg(monkeypatch, {ks.RUTAS: BG_RUTAS}, 'n99')
    assert not ks.sync_bg_code()
    assert written[ks.BG_CODE_FILE] == 'n99'
    assert ks.RUTAS not in written and flags == []


def test_blackghost_is_never_opened_in_the_background_without_a_saved_code(monkeypatch):
    # Sin código guardado, "INGRESAR AL ADDON" abre un teclado: desde el servicio se quedaría en pantalla.
    written, flags, listed = fake_bg(monkeypatch, {ks.RUTAS: BG_RUTAS, ks.MENU_VERSION_FILE: '3'}, '')
    assert ks.refresh_menu_if_outdated()
    assert not any('blackghost' in p for p in listed)
    assert json.loads(written.get(ks.RUTAS, BG_RUTAS))['blackghost'] == json.loads(BG_RUTAS)['blackghost']


def test_older_menu_also_finds_the_blackghost_rows_again(monkeypatch):
    written, flags, _ = fake_bg(monkeypatch, {ks.RUTAS: BG_RUTAS, ks.MENU_VERSION_FILE: '3',
                                              ks.BG_CODE_FILE: 'n17'}, 'n17')
    assert ks.refresh_menu_if_outdated()
    bg = json.loads(written[ks.RUTAS])['blackghost']
    assert 'canales' in bg['deportes'] and bg['codigo'] == 'n17'
    assert flags == [True]


def test_key_pasted_as_the_omdb_example_url_keeps_only_the_key():
    # OMDb manda por correo "http://www.omdbapi.com/?i=tt3896198&apikey=XXXX": pegada entera, TMDb Helper daba 401.
    assert ks.clean_key('http://www.omdbapi.com/? i=tt3896198&apikey=f525ce5d') == 'f525ce5d'
    assert ks.clean_key('https://www.omdbapi.com/?apikey=ab12&i=tt1') == 'ab12'
    assert ks.clean_key('  f525ce5d ') == 'f525ce5d'
    assert ks.clean_key('') == ''


def test_tmdbhelper_gets_the_clean_omdb_key(monkeypatch):
    saved = {}

    class Helper(object):
        def setSettingInt(self, sid, value):
            saved[sid] = value

        def setSetting(self, sid, value):
            saved[sid] = value
    monkeypatch.setattr(ks, 'has_addon', lambda a: True)
    monkeypatch.setattr(ks.xbmcaddon, 'Addon', lambda a=None: Helper())
    monkeypatch.setattr(ks, 'setting', lambda sid: 'http://www.omdbapi.com/? i=tt3896198&apikey=f525ce5d')
    assert ks.apply_tmdbhelper()
    assert saved['omdb_apikey'] == 'f525ce5d'


# --- Copias de las filas de Palantir (filas.py) ---

def test_saved_row_is_read_back_and_listed_in_the_index(monkeypatch):
    written, _ = fake_menu_files(monkeypatch, {})
    monkeypatch.setattr(ks.xbmcvfs, 'listdir', lambda p: ([], sorted(
        f[len(p):] for f in written if f.startswith(p) and '/' not in f[len(p):])))
    assert ks.load_fila('peliculas.estrenos') is None and ks.load_fila_index() == {}
    entry = {'path': 'plugin://p/?e', 'time': 100.0, 'items': [{'label': 'A'}]}
    ks.save_fila('peliculas.estrenos', entry)
    assert ks.load_fila('peliculas.estrenos') == entry
    assert ks.load_fila_index() == {'peliculas.estrenos': {'path': 'plugin://p/?e', 'time': 100.0}}
    ks.save_fila('series.nuevas', dict(entry, path='plugin://p/?n'))
    assert set(ks.load_fila_index()) == {'peliculas.estrenos', 'series.nuevas'}


def test_row_is_fetched_with_every_field_the_skin_shows(monkeypatch):
    from resources.lib import filas
    asked = []
    monkeypatch.setattr(ks, 'rpc', lambda method, params=None: asked.append((method, params)) or {'files': [{'a': 1}]})
    assert ks.fetch_row('plugin://p/?e') == [{'a': 1}]
    assert asked == [('Files.GetDirectory', {'directory': 'plugin://p/?e', 'media': 'video',
                                             'properties': filas.FIELDS})]


def test_fetch_row_tells_a_failure_from_an_empty_list(monkeypatch):
    monkeypatch.setattr(ks, 'rpc', lambda method, params=None: {})  # error de JSON-RPC (rpc ya lo registra)
    assert ks.fetch_row('plugin://p/?e') is None
    monkeypatch.setattr(ks, 'rpc', lambda method, params=None: {'limits': {'total': 0}})
    assert ks.fetch_row('plugin://p/?e') == []


def test_each_row_has_its_own_meta_file_so_two_writers_never_lose_each_other(monkeypatch):
    written, _ = fake_menu_files(monkeypatch, {})
    entry = {'path': 'plugin://p/?e', 'time': 100.0, 'items': [{'label': 'A'}]}
    ks.save_fila('peliculas.estrenos', entry)
    assert json.loads(written[ks.FILAS + 'peliculas.estrenos.meta']) == {'path': 'plugin://p/?e', 'time': 100.0}
    assert ks.FILAS_INDEX not in written  # ya no hay un índice común que leer y reescribir


def test_write_file_replaces_the_file_in_one_step(monkeypatch):
    import importlib
    import resources.lib.kodi_setup as real
    importlib.reload(real)  # sin los monkeypatch de otros tests
    ops = []

    class FakeFile(object):
        def __init__(self, path, mode):
            ops.append(('open', path))

        def write(self, data):
            ops.append(('write', bytes(data)))
            return True

        def close(self):
            ops.append(('close',))
    monkeypatch.setattr(real.xbmcvfs, 'File', FakeFile)
    monkeypatch.setattr(real.xbmcvfs, 'mkdirs', lambda p: True)
    monkeypatch.setattr(real.xbmcvfs, 'rename', lambda a, b: ops.append(('rename', a, b)) or True)
    real.write_file('special://profile/x/a.json', '{}')
    tmp = ops[0][1]
    assert tmp != 'special://profile/x/a.json' and tmp.startswith('special://profile/x/a.json')
    assert ops[1:] == [('write', b'{}'), ('close',), ('rename', tmp, 'special://profile/x/a.json')]


def test_load_fila_only_accepts_the_known_rows(monkeypatch):
    read = []
    monkeypatch.setattr(ks, 'read_file', lambda p: read.append(p) or '')
    assert ks.load_fila('../../../../favourites') is None and read == []


def test_sports_art_is_saved_and_read_back(monkeypatch):
    fake_menu_files(monkeypatch, {})
    assert ks.load_arte() == {}
    ks.save_arte({'sports': {'Soccer': 'https://x/s.jpg'}, 'sports_time': 1})
    assert ks.load_arte() == {'sports': {'Soccer': 'https://x/s.jpg'}, 'sports_time': 1}


def test_palantir_db_prefers_the_addon_file_then_the_profile_copy(monkeypatch):
    monkeypatch.setattr(ks.xbmcvfs, 'translatePath', lambda p: '/k/' + p.split('://', 1)[1])
    for present, expected in (({ks.PALANTIR_DB[0], ks.PALANTIR_DB[1]}, '/k/home/addons/plugin.video.palantir3/moria.cm3'),
                              ({ks.PALANTIR_DB[1]}, '/k/profile/addon_data/script.module/settings.xml'),
                              (set(), None)):  # Palantir sin instalar o sin su base
        monkeypatch.setattr(ks.xbmcvfs, 'exists', lambda p, s=present: p in s)
        assert ks.palantir_db() == expected


def test_patches_cover_the_search_texts_of_af3_and_skinvariables():
    targets = {(a, f) for a, f, _, _ in ks.PATCHES}
    assert (ks.SKIN, pt.AF3_STRINGS_FILE) in targets
    assert ('script.skinvariables', pt.SKINVARIABLES_STRINGS_FILE) in targets
