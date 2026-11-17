# -*- coding: utf-8 -*-
"""Genera el "preset" de Arctic Fuse 3 (los JSON de script.skinvariables) y las
órdenes de skin que lo aplican. Puro: sin Kodi."""
import json

from resources.lib.discover import DEPORTES, needs_trakt

SKIN = 'skin.arctic.fuse.3'
FILE = 'skinvariables-shortcut-%s.json'
FAVOURITES = 'favourites://'
# Súbelo cuando cambie el formato del menú: las cajas que ya lo tienen montado lo vuelven a aplicar al arrancar.
# 3: filas sin las listas de Palantir que piden Trakt ("Más vistas"), con "Recién añadidas" y "Nuevas series".
# 4: Deportes con las agendas reales de BlackGhost (no tiene carpetas por deporte).
MENU_VERSION = 4
# Kodi recarga las filas "sin orden" cada vez que empieza o acaba cualquier reproducción (para actualizar lo
# visto). Con las de Palantir eso ocupaba Python 15 s tras cada tráiler y el siguiente esperaba. Con un orden fijo
# no las recarga; "track" no cambia nada en películas y series (todas valen 0) y se respeta el orden de Palantir.
ROW_SORT = 'track'

# Filas de Deportes bajo la agenda: lo de España primero y luego los deportes que nombró tu padre (BlackGhost no
# tiene pádel; F1 y MotoGP van juntos en "Motor").
ORDEN_DEPORTES = ['espana', 'futbol', 'baloncesto', 'nfl', 'motor', 'f1', 'ufc', 'canales']

ICONOS_DEPORTES = {
    'agenda': 'calendar-day', 'espana': 'flag', 'futbol': 'futbol', 'baloncesto': 'basketball',
    'nfl': 'football-american', 'motor': 'motorcycle', 'f1': 'flag-checkered', 'ufc': 'hand-fist',
    'canales': 'satellite-dish',
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

# Lo que hace AF3 en su primer arranque (shortcuts/skinvariables-startup.json), menos abrir su asistente y poner
# su destacado de Inicio. Si las recargas de skin del primer arranque se lo comen, lo terminamos nosotros; si no,
# AF3 lo repetiría en el siguiente arranque y sacaría su asistente encima del menú.
AF3_FIRST_RUN = [
    'Skin.SetBool(TMDbHelper.EnableData)',
    'Skin.SetBool(TMDbHelper.EnableCrop)',
    'Skin.SetBool(TMDbHelper.EnableBlur)',
    'Skin.SetBool(TMDbHelper.Service)',
    'Skin.SetString(Background.DialogImage,Adaptive)',
    'Skin.SetString(Background.Image,special://skin/extras/backgrounds/blur/purple_blur.jpg)',
    'Skin.SetString(HomeSwitcher.Home.Shortcut.Path,ActivateWindow(1181))',
    'Skin.SetBool(DefaultConfig.InitDone)',
]

# Secciones con línea de botones bajo el menú (saltar a un deporte sin bajar 8 filas).
SUBMENU = {'1104'}


def icon(name):
    return 'special://skin/extras/icons/%s.png' % name


def _row(label, path, style=None):
    item = {'label': label, 'icon': '', 'path': path, 'target': 'videos', 'widget_sortby': ROW_SORT}
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


def _usable(group):
    # Las rutas guardadas por versiones anteriores pueden traer listas de Palantir que ahora piden Trakt.
    return {key: item for key, item in (group or {}).items() if not needs_trakt(item.get('label'))}


def _parts(rutas):
    pal = rutas.get('palantir') or {}
    bg = rutas.get('blackghost') or {}
    return _usable(pal.get('peliculas')), _usable(pal.get('series')), bg.get('agenda'), bg.get('deportes') or {}


def _sections(rutas):
    """{ventana: [(etiqueta, ruta, icono, estilo)]} con solo lo que existe."""
    pel, ser, agenda, dep = _parts(rutas)

    def pick(group, spec, style):
        return [(label, group[k]['path'], ico, style) for k, label, ico in spec if k in group]

    generos = [('generos', 'Géneros', 'genre')]
    pel_rows = pick(pel, [('estrenos', 'Estrenos', 'recentlyadded'), ('recientes', 'Recién añadidas', 'film'),
                          ('populares', 'Populares', 'fire-flame-curved'), ('valoradas', 'Mejor valoradas', 'star')],
                    'Poster') + pick(pel, generos, None)
    ser_rows = pick(ser, [('novedades', 'Nuevos episodios', 'recentlyadded'), ('nuevas', 'Nuevas series', 'tv'),
                          ('emision', 'En emisión', 'tv'), ('populares', 'Populares', 'fire-flame-curved'),
                          ('valoradas', 'Mejor valoradas', 'star')], 'Poster') + pick(ser, generos, None)
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
    files[FILE % '1109widgets'] = [_row('Mis favoritos', FAVOURITES, 'Poster')]
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
    home.append(_row('Mis favoritos', FAVOURITES, 'Poster'))
    files[FILE % 'homewidgets'] = home
    files[FILE % 'homesubmenu'] = []
    return files


def _quote(value):
    return '"%s"' % value


def _named(group, *choices):
    """(lista, nombre) de la primera que exista de (clave, nombre), o (None, '')."""
    for key, label in choices:
        if key in group:
            return group[key], label
    return None, ''


def _spotlight(window, item, label):
    out = ['Skin.Reset(HomeSwitcher.%s.Spotlight.%s)' % (window, k) for k in SPOTLIGHT_KEYS]
    if item:
        out += ['Skin.SetString(HomeSwitcher.%s.Spotlight.Path,%s)' % (window, _quote(item['path'])),
                'Skin.SetString(HomeSwitcher.%s.Spotlight.Target,videos)' % window,
                'Skin.SetString(HomeSwitcher.%s.Spotlight.Label,%s)' % (window, label)]
    return out


def skin_builtins(rutas, preset_folder, now, first_run=False):
    pel, ser, agenda, _ = _parts(rutas)
    folder = preset_folder if preset_folder.endswith('/') else preset_folder + '/'
    out = list(AF3_FIRST_RUN) if first_run else []
    # AF3 guarda "$LOCALIZE[10000]" sin traducir y el menú lo enseña tal cual.
    out.append('Skin.SetString(HomeSwitcher.Home.Name,Inicio)')
    for win, kind, mode in HUB_TYPES:
        out += ['Skin.SetString(HomeSwitcher.%s.Type,%s)' % (win, kind),
                'Skin.SetString(HomeSwitcher.%s.Mode,%s)' % (win, mode)]
    out += _spotlight('Home', *_named(pel, ('estrenos', 'Estrenos'), ('recientes', 'Recién añadidas'),
                                      ('populares', 'Populares')))
    out += _spotlight('1101', *_named(pel, ('populares', 'Populares'), ('recientes', 'Recién añadidas'),
                                      ('estrenos', 'Estrenos')))
    out += _spotlight('1102', *_named(ser, ('populares', 'Populares'), ('nuevas', 'Nuevas series'),
                                      ('novedades', 'Nuevos episodios'), ('emision', 'En emisión')))
    out += _spotlight('1103', _first(pel, 'estrenos') or _first(ser, 'novedades', 'emision'), 'Novedades')
    out += _spotlight('1104', agenda, 'Agenda de hoy')
    out += _spotlight('1109', None, '')
    # Interruptores con SetBool(…,false): Skin.Reset(x) se queda en el texto x si existe y no apaga el interruptor.
    out += ['Skin.SetString(CustomRating.Movies.Item01,IMDb)',
            'Skin.SetString(CustomRating.TVShows.Item01,IMDb)',
            'Skin.SetBool(TMDbHelper.DisableRatings,false)',
            'RunScript(script.skinvariables,copy_menufolder=%s,skin=%s,force=True)' % (folder, SKIN),
            'Skin.SetString(Shortcuts.RebuildDateTime,%s)' % now,
            'Skin.SetBool(SetupWizard.Pending,false)',
            # Lo mismo que hace la skin al volver al Inicio: reconstruye los menús con la fecha nueva.
            'RunScript(script.skinvariables,"run_executebuiltin=special://skin/shortcuts/'
            'skinvariables-build-templates.json",use_rules)']
    return out


def write_preset(files, folder, writer):
    folder = folder if folder.endswith('/') else folder + '/'
    for name, data in files.items():
        writer(folder + name, json.dumps(data, indent=4, ensure_ascii=False))
