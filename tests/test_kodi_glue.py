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


def test_service_starts_even_without_requests_module(monkeypatch):
    import importlib
    import sys
    monkeypatch.setitem(sys.modules, 'requests', None)  # import requests -> ImportError
    sys.modules.pop('service', None)
    service = importlib.import_module('service')
    assert callable(service.http_get)
