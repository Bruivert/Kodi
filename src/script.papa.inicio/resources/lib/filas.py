# -*- coding: utf-8 -*-
"""Copia de las filas de Palantir, como hace AutoWidget en otras skins.

Arctic Fuse 3 abre cada sección como una ventana y, cada vez que se entra (aunque solo se pase de largo con el
foco), vuelve a pedir todas sus filas. Kodi ejecuta los addons de Python de uno en uno y cada lista de Palantir
cuesta ~6 s (30 s al encender, compitiendo con todo): llegar a Favoritos costaba más de un minuto. Las filas se
sirven desde una copia (plugin.py, <1 s) que el servicio renueva por detrás, de una en una. Puro: sin Kodi.
"""
from urllib.parse import unquote, urlencode

from resources.lib import balandro
from resources.lib.discover import needs_trakt

BASE = 'plugin://script.papa.inicio/'
GROUPS = ('peliculas', 'series')
# Filas de Deportes (BlackGhost). Cada una tarda 3-7 s (17 s al encender) y Kodi las pide de pocas en pocas, en una
# sola cola para todas las secciones. Los demás deportes van en los botones bajo el menú, que no cargan nada.
FILAS_DEPORTES = ['agenda', 'espana', 'futbol', 'motor', 'canales']

# Lo que se pide a Kodi de cada elemento (Files.GetDirectory): todo lo que Palantir pone y la skin enseña.
FIELDS = ['title', 'year', 'plot', 'rating', 'votes', 'genre', 'runtime', 'mpaa', 'premiered', 'studio', 'country',
          'tagline', 'originaltitle', 'imdbnumber', 'uniqueid', 'art', 'showtitle', 'season', 'episode', 'trailer',
          'director', 'customproperties']

# Campo de Files.GetDirectory → clave de ListItem.setInfo('video', …).
INFO = {'title': 'title', 'year': 'year', 'plot': 'plot', 'rating': 'rating', 'votes': 'votes', 'genre': 'genre',
        'runtime': 'duration', 'mpaa': 'mpaa', 'premiered': 'premiered', 'studio': 'studio', 'country': 'country',
        'tagline': 'tagline', 'originaltitle': 'originaltitle', 'imdbnumber': 'imdbnumber',
        'showtitle': 'tvshowtitle', 'season': 'season', 'episode': 'episode', 'trailer': 'trailer',
        'director': 'director'}
MEDIATYPES = {'movie', 'tvshow', 'season', 'episode', 'musicvideo', 'video', 'set'}


def row_paths(rutas):
    """{'peliculas.estrenos': ruta, 'deportes.agenda': ruta de BlackGhost} de las listas que forman filas (nunca las
    de Palantir que piden Trakt). Con Balandro instalado, las filas de Palantir se llenan con su lista equivalente de
    Balandro (balandro.FILAS): mismas filas y nombres, otra fuente."""
    pal = (rutas or {}).get('palantir') or {}
    rows = {'%s.%s' % (group, key): item['path']
            for group in GROUPS for key, item in sorted((pal.get(group) or {}).items())
            if item.get('path') and not needs_trakt(item.get('label'))}
    bg = (rutas or {}).get('blackghost') or {}
    sports = dict(bg.get('deportes') or {}, agenda=bg.get('agenda'))
    rows.update({'deportes.%s' % key: sports[key]['path'] for key in FILAS_DEPORTES
                 if (sports.get(key) or {}).get('path')})
    if (rutas or {}).get('balandro'):
        rows.update({key: balandro.row_url(key) for key in rows if key in balandro.FILAS})
    return rows


def max_age(key):
    """Segundos que vale una copia: la agenda de deportes cambia a lo largo del día."""
    return SPORTS_MAX_AGE if key.startswith('deportes.') else MAX_AGE


def fila_url(key):
    return BASE + '?' + urlencode({'fila': key})


def unwrap_image(value):
    """"image://https%3a%2f%2f…/" (como lo devuelve Kodi) → "https://…"."""
    if value and value.startswith('image://') and value.endswith('/'):
        return unquote(value[len('image://'):-1])
    return value or ''


def _empty(value):
    return value in (None, '', [], {}, -1) or (isinstance(value, (int, float)) and value == 0 and value is not True)


def to_item(f):
    """Lo necesario para rehacer el ListItem igual que lo dio Palantir."""
    props = dict(f.get('customproperties') or {})
    playable = props.pop('isplayable', '')
    folder = f.get('filetype') == 'directory'
    if not folder:
        props['IsPlayable'] = 'true' if playable == 'true' else 'false'
    art = {name: unwrap_image(url) for name, url in (f.get('art') or {}).items() if url}
    if 'thumb' not in art and f.get('thumbnail'):
        art['thumb'] = unwrap_image(f['thumbnail'])
    if 'thumb' not in art and art.get('poster'):
        art['thumb'] = art['poster']
    info = {INFO[k]: v for k, v in f.items() if k in INFO and not _empty(v)}
    if f.get('type') in MEDIATYPES:
        info['mediatype'] = f['type']
    return {'label': f.get('label', ''), 'path': f.get('file', ''), 'folder': folder, 'art': art, 'info': info,
            'uniqueids': dict(f.get('uniqueid') or {}), 'properties': props}


def content(items):
    kinds = {i['info'].get('mediatype') for i in items}
    if kinds == {'movie'}:
        return 'movies'
    if kinds == {'tvshow'}:
        return 'tvshows'
    return 'videos'


def entry(path, files, now):
    return {'path': path, 'time': now, 'items': [to_item(f) for f in files or []]}


def usable(cached, path):
    return bool(cached and cached.get('path') == path)


def keeps(files, key):
    """Si la respuesta vale como copia. None es un fallo de red; una lista vacía solo vale en Deportes (la agenda puede
    quedarse sin partidos, o el código de BlackGhost caducar: mejor vacía que los partidos de ayer). "Estrenos" vacía
    es que Palantir ha fallado: se queda la copia anterior."""
    return files is not None and (bool(files) or key.startswith('deportes.'))


def next_to_refresh(rows, index, now):
    """La fila que toca renovar: primero las que no tienen copia (o cuya lista cambió), luego la más vieja."""
    stale = []
    for key, path in sorted(rows.items()):
        meta = (index or {}).get(key)
        if not meta or meta.get('path') != path:
            return key
        if now - meta.get('time', 0) >= max_age(key):
            stale.append((meta.get('time', 0), key))
    return min(stale)[1] if stale else None


START_DELAY = 120  # s tras encender: que Kodi y la skin terminen de arrancar
GAP = 20  # s entre lista y lista
MAX_AGE = 3600  # s: cada lista de Palantir se renueva como mucho una vez por hora
SPORTS_MAX_AGE = 900  # s: las de BlackGhost, cada cuarto de hora
FAIL_WAIT = 300  # s de espera si Palantir no contesta


class Refresher(object):
    """Renueva las copias de una en una desde el servicio, cuando la caja está tranquila (como AutoWidget)."""

    def __init__(self, rows, index, fetch, save, can_run, clock):
        self.rows, self.index, self.fetch, self.save, self.can_run, self.clock = rows, index, fetch, save, can_run, clock
        self.started = clock()
        self.next_time = self.started + START_DELAY

    def tick(self):
        """La fila renovada (o intentada) en esta vuelta, o None."""
        now = self.clock()
        if now < self.next_time or not self.can_run():
            return None
        rows = self.rows()
        key = next_to_refresh(rows, self.index(), now)
        self.next_time = now + GAP
        if not key:
            return None
        files = self.fetch(rows[key])
        if keeps(files, key):
            self.save(key, entry(rows[key], files, self.clock()))
        else:  # sin red o Palantir con problemas: se queda la copia anterior
            self.next_time = now + FAIL_WAIT
        return key
