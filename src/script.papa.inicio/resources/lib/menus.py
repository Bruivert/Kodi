# -*- coding: utf-8 -*-
"""Genera el "preset" de Arctic Fuse 3 (los JSON de script.skinvariables) y las
órdenes de skin que lo aplican. Puro: sin Kodi."""
import json

from resources.lib.discover import DEPORTES

SKIN = 'skin.arctic.fuse.3'
FILE = 'skinvariables-shortcut-%s.json'
FAVOURITES = 'favourites://'

# Orden en el que tu padre nombró los deportes.
ORDEN_DEPORTES = ['futbol', 'baloncesto', 'nfl', 'padel', 'f1', 'motogp', 'ufc']

ICONOS_DEPORTES = {
    'agenda': 'calendar-day', 'futbol': 'futbol', 'baloncesto': 'basketball', 'nfl': 'football-american',
    'padel': 'table-tennis-paddle-ball', 'f1': 'flag-checkered', 'motogp': 'motorcycle', 'ufc': 'hand-fist',
}

# (ventana, slot, etiqueta, icono). 1106-1108 se dejan como en la skin, desactivadas.
HUBS = [
    ('1101', '01', 'Películas', 'film'),
    ('1102', '02', 'Series', 'tv'),
    ('1103', '03', 'Novedades', 'recentlyadded'),
    ('1104', '04', 'Deportes', 'trophy'),
    ('1106', '06', '$LOCALIZE[31605]', 'calendar'),
    ('1107', '07', '$LOCALIZE[31085] / PVR', 'livetv'),
    ('1108', '08', '$LOCALIZE[24001]', 'addon'),
    ('1109', '09', 'Favoritos', 'heart'),
]

HUB_TYPES = [
    ('1101', 'Custom', 'Standard'), ('1102', 'Custom', 'Standard'), ('1103', 'Custom', 'Standard'),
    ('1104', 'Custom', 'Standard'), ('1106', 'NextAired', 'Standard'), ('1107', 'LiveTV', 'Wall'),
    ('1108', 'Addons', 'Wall'), ('1109', 'Custom', 'Standard'),
]

SPOTLIGHT_KEYS = ['Path', 'Target', 'Label', 'SortMethod', 'SortOrder', 'Limit']

# Secciones con línea de botones bajo el menú (saltar a un deporte sin bajar 8 filas).
SUBMENU = {'1104'}


def icon(name):
    return 'special://skin/extras/icons/%s.png' % name


def _row(label, path, style=None):
    item = {'label': label, 'icon': '', 'path': path, 'target': 'videos'}
    if style:
        item['widget_style'] = style
    return item


def _link(label, path, icon_name):
    return {'label': label, 'icon': icon(icon_name), 'path': path, 'target': 'videos'}


def _first(group, *keys):
    for k in keys:
        if k in group:
            return group[k]
    return None


def _parts(rutas):
    pal = rutas.get('palantir') or {}
    bg = rutas.get('blackghost') or {}
    return pal.get('peliculas') or {}, pal.get('series') or {}, bg.get('agenda'), bg.get('deportes') or {}


def _sections(rutas):
    """{ventana: [(etiqueta, ruta, icono, estilo)]} con solo lo que existe."""
    pel, ser, agenda, dep = _parts(rutas)

    def pick(group, spec, style):
        return [(label, group[k]['path'], ico, style) for k, label, ico in spec if k in group]

    generos = [('generos', 'Géneros', 'genre')]
    pel_rows = pick(pel, [('estrenos', 'Estrenos', 'recentlyadded'), ('populares', 'Populares', 'fire-flame-curved'),
                          ('valoradas', 'Mejor valoradas', 'star')], 'Poster') + pick(pel, generos, None)
    ser_rows = pick(ser, [('novedades', 'Nuevos episodios', 'recentlyadded'), ('emision', 'En emisión', 'tv'),
                          ('populares', 'Populares', 'fire-flame-curved'), ('valoradas', 'Mejor valoradas', 'star')],
                    'Poster') + pick(ser, generos, None)
    nov_rows = []
    if 'estrenos' in pel:
        nov_rows.append(('Estrenos de cine', pel['estrenos']['path'], 'film', 'Poster'))
    serie_nueva = _first(ser, 'novedades', 'emision')
    if serie_nueva:
        nov_rows.append(('Series nuevas', serie_nueva['path'], 'tv', 'Poster'))
    dep_rows = []
    if agenda:
        dep_rows.append((DEPORTES['agenda']['label'], agenda['path'], ICONOS_DEPORTES['agenda'], None))
    for k in ORDEN_DEPORTES:
        if k in dep:
            dep_rows.append((DEPORTES[k]['label'], dep[k]['path'], ICONOS_DEPORTES[k], None))
    return {'1101': pel_rows, '1102': ser_rows, '1103': nov_rows, '1104': dep_rows}


def build_preset(rutas):
    files = {}
    sections = _sections(rutas)
    enabled = {'1109'} | {w for w, rows in sections.items() if rows}
    files[FILE % 'hubs'] = [
        {'label': label, 'icon': icon(ico), 'path': '', 'target': '', 'window': win, 'slot': slot,
         'disabled': '' if win in enabled else 'True'}
        for win, slot, label, ico in HUBS
    ]
    for win, rows in sections.items():
        files[FILE % ('%swidgets' % win)] = [_row(label, path, style) for label, path, _, style in rows]
        # Botones bajo el menú solo donde ahorran camino (Deportes); en el resto repetirían las filas.
        submenu = rows if win in SUBMENU else []
        files[FILE % ('%ssubmenu' % win)] = [_link(label, path, ico) for label, path, ico, _ in submenu]
    files[FILE % '1109widgets'] = [_row('Mis favoritos', FAVOURITES)]
    files[FILE % '1109submenu'] = []

    pel, ser, agenda, dep = _parts(rutas)
    home = []
    if 'estrenos' in pel:
        home.append(_row('Estrenos', pel['estrenos']['path'], 'Poster'))
    serie_nueva = _first(ser, 'novedades', 'emision')
    if serie_nueva:
        home.append(_row('Series nuevas', serie_nueva['path'], 'Poster'))
    deportes_hoy = agenda or next((dep[k] for k in ORDEN_DEPORTES if k in dep), None)
    if deportes_hoy:
        home.append(_row('Deportes hoy', deportes_hoy['path']))
    home.append(_row('Mis favoritos', FAVOURITES))
    files[FILE % 'homewidgets'] = home
    files[FILE % 'homesubmenu'] = []
    return files


def _quote(value):
    return '"%s"' % value


def _spotlight(window, item, label):
    out = ['Skin.Reset(HomeSwitcher.%s.Spotlight.%s)' % (window, k) for k in SPOTLIGHT_KEYS]
    if item:
        out += ['Skin.SetString(HomeSwitcher.%s.Spotlight.Path,%s)' % (window, _quote(item['path'])),
                'Skin.SetString(HomeSwitcher.%s.Spotlight.Target,videos)' % window,
                'Skin.SetString(HomeSwitcher.%s.Spotlight.Label,%s)' % (window, label)]
    return out


def skin_builtins(rutas, preset_folder, now):
    pel, ser, agenda, _ = _parts(rutas)
    folder = preset_folder if preset_folder.endswith('/') else preset_folder + '/'
    out = []
    for win, kind, mode in HUB_TYPES:
        out += ['Skin.SetString(HomeSwitcher.%s.Type,%s)' % (win, kind),
                'Skin.SetString(HomeSwitcher.%s.Mode,%s)' % (win, mode)]
    out += _spotlight('Home', _first(pel, 'estrenos', 'populares'), 'Estrenos')
    out += _spotlight('1101', _first(pel, 'populares', 'estrenos'), 'Populares')
    out += _spotlight('1102', _first(ser, 'populares', 'novedades', 'emision'), 'Populares')
    out += _spotlight('1103', _first(pel, 'estrenos') or _first(ser, 'novedades', 'emision'), 'Novedades')
    out += _spotlight('1104', agenda, 'Agenda de hoy')
    out += _spotlight('1109', None, '')
    out += ['Skin.SetString(CustomRating.Movies.Item01,IMDb)',
            'Skin.SetString(CustomRating.TVShows.Item01,IMDb)',
            'Skin.Reset(TMDbHelper.DisableRatings)',
            'RunScript(script.skinvariables,copy_menufolder=%s,skin=%s,force=True)' % (folder, SKIN),
            'Skin.SetString(Shortcuts.RebuildDateTime,%s)' % now,
            'Skin.Reset(SetupWizard.Pending)',
            # Lo mismo que hace la skin al volver al Inicio: reconstruye los menús con la fecha nueva.
            'RunScript(script.skinvariables,"run_executebuiltin=special://skin/shortcuts/'
            'skinvariables-build-templates.json",use_rules)']
    return out


def write_preset(files, folder, writer):
    folder = folder if folder.endswith('/') else folder + '/'
    for name, data in files.items():
        writer(folder + name, json.dumps(data, indent=4, ensure_ascii=False))
