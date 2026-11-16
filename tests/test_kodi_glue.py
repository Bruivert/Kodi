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
    assert {'tmdb_key', 'omdb_key', 'trailers_auto'} <= ids


def test_entry_points_compile():
    for name in ('default.py', 'service.py'):
        py_compile.compile(os.path.join(ADDON_DIR, name), doraise=True)


def test_summary_counts_rows_and_names_sports():
    rutas = {'palantir': {'peliculas': {'estrenos': {}, 'populares': {}, 'valoradas': {}, 'generos': {}},
                          'series': {'novedades': {}, 'emision': {}}},
             'blackghost': {'agenda': {'path': 'x'}, 'deportes': {'futbol': {}, 'ufc': {}}}}
    text = ks.summary(rutas)
    assert 'Películas: 4 filas' in text and 'Series: 2 filas' in text
    assert 'Deportes: Agenda de hoy, Fútbol, UFC' in text


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
