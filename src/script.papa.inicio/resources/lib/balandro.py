# -*- coding: utf-8 -*-
"""Ver por Balandro: pulsar una película o un capítulo y que se reproduzca.

Palantir cerró (17/11/2026). Las fichas (lupa y filas) llevan a las rutas del asistente ?play= (película o capítulo,
reproducible) y ?serie= (temporadas). Para saber dónde ver una ficha se busca su título en Balandro y se dejan solo los
resultados de esa ficha: mismo id de TMDb o, si la web no lo da, mismo título y año.

La búsqueda de Balandro en todas sus webs tarda ~15 s en la caja, y lanzar varias webs a la vez es peor (cada una es un
Python y la caja se satura: ~10 s). Por eso se pregunta a una web cada vez, en el orden de FAST (las que más tienen en
las pruebas del 23/11/2026, ~2 s cada una), y se para en la primera que lo tiene; si ninguna, la búsqueda en todas.
Puro: las búsquedas y los datos de los canales llegan de fuera.
"""
import base64
import json
from urllib import parse

from resources.lib import calidad
from resources.lib import catalogo
from resources.lib.discover import clean, normalize
from resources.lib.fichas import papa_url, play_url, serie_url

BALANDRO = 'plugin://plugin.video.balandro/?'
SEARCH_TYPES = {'peliculas': 'movie', 'series': 'tvshow'}
MAX_AGE = 86400  # s: lo encontrado para una ficha vale un día (volver a pulsarla no repite la búsqueda)
RETRY = 600  # s: si se vuelve a pulsar antes y la fuente anterior no llegó a arrancar, se prueba la siguiente
# Webs a las que se pregunta una a una. Solo torrents en castellano (CASTELLANO), que dicen su calidad o su tamaño: con el
# mínimo de 1080p las de streaming (no la dicen) y las latinas (PelisPanda, CineCalidad…) quedan fuera. PasateATorrent
# tenía 37 de sus 60 últimas películas en 1080p o 4K; DonTorrent, más series en castellano (temporadas «[1080p]»).
FAST = {'peliculas': ('pasateatorrent', 'dontorrents'), 'series': ('dontorrents', 'pasateatorrent')}
CASTELLANO = ('pasateatorrent', 'dontorrents', 'elitetorrent', 'elitetorrentnz', 'grantorrent', 'divxtotal',
              'mejortorrentapp')


def _encode(item):
    """Como Item.tourl de Balandro: el dict en JSON y base64. Así el título viaja entero aunque lleve & o =."""
    return BALANDRO + parse.quote(base64.b64encode(json.dumps(item).encode('utf-8')))


def decode(path):
    """El item de Balandro de una dirección suya, o None (cabeceras de canal, direcciones sin item)."""
    query = (path or '').split('?', 1)[1] if '?' in (path or '') else ''
    if not query or 'action=' in query:
        return None
    try:
        item = json.loads(base64.b64decode(parse.unquote(query)).decode('utf-8'))
    except ValueError:
        return None
    return item if isinstance(item, dict) else None


def search_url(kind, title, channel='search'):
    """La búsqueda de Balandro con el texto ya escrito (item.buscando: no saca el teclado). Con channel, solo en esa
    web; sin él, en todas."""
    return _encode({'channel': channel, 'action': 'search', 'search_type': SEARCH_TYPES[kind], 'buscando': title})


def _matches(item, tmdb, title, year):
    info = item.get('infoLabels') or {}
    if info.get('tmdb_id'):
        return str(info['tmdb_id']) == str(tmdb)
    name = item.get('contentTitle') or item.get('contentSerieName') or ''
    if catalogo.normalize(name) != catalogo.normalize(title):
        return False
    try:
        return not info.get('year') or not year or abs(int(info['year']) - int(year)) <= 1
    except (TypeError, ValueError):
        return True


def sources(files, tmdb, title, year, channel, torrent_only=True, allowed=CASTELLANO):
    """Los resultados de la búsqueda que son esta ficha, los torrents en castellano primero y, en cada web, primero los
    que se llaman igual. 'other' es el título de la web si no es el de la ficha (otra versión o página con el mismo id).
    channel(id) da {'name', 'torrent', 'cast'} o None. Con torrent_only, solo webs de torrent (las únicas que dicen
    calidad o tamaño) y de allowed (en castellano)."""
    found, seen = [], set()
    for f in files:
        item = decode(f.get('file'))
        if not item or not item.get('channel') or f['file'] in seen or not _matches(item, tmdb, title, year):
            continue
        seen.add(f['file'])
        info = channel(item['channel']) or {}
        if torrent_only and (not info.get('torrent') or (allowed and item['channel'] not in allowed)):
            continue
        name = item.get('contentTitle') or item.get('contentSerieName') or ''
        found.append({'channel': item['channel'], 'name': info.get('name') or item['channel'],
                      'torrent': bool(info.get('torrent')), 'cast': bool(info.get('cast')),
                      'other': name if catalogo.normalize(name) != catalogo.normalize(title) else '',
                      'path': f['file'], 'folder': f.get('filetype') == 'directory', 'label': f.get('label', ''),
                      'url': item.get('url') or ''})
    found.sort(key=lambda s: (not s['torrent'], not s['cast'], bool(s['other'])))
    for s in found:
        del s['cast']
    return found


def channel_info(text):
    """De channels/<id>.json de Balandro: nombre, si es de torrent y si tiene castellano."""
    try:
        data = json.loads(text or '')
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return {'name': data.get('name') or '', 'torrent': 'torrent' in (data.get('categories') or []),
            'cast': 'cast' in (data.get('language') or [])}


def fresh(entry, now):
    return bool(entry and entry.get('sources')) and now - entry.get('time', 0) < MAX_AGE


def failed(last, path, now):
    """Si path es la última fuente probada (last: {'fuente', 'time', 'ok'}) y no llegó a arrancar hace poco."""
    return bool(last) and last.get('fuente') == path and not last.get('ok') and now - last.get('time', 0) < RETRY


def pick(paths, last, now):
    """La fuente que toca: la primera, salvo que la última probada no arrancara hace poco; entonces la siguiente.
    None si no hay."""
    if not paths:
        return None
    if last and last.get('fuente') in paths and failed(last, last['fuente'], now):
        return paths[(paths.index(last['fuente']) + 1) % len(paths)]
    return paths[0]


# --- Las filas del menú (las de Palantir) con su lista equivalente de Balandro ---

RECIENTES = {'peliculas': {'channel': 'pasateatorrent', 'action': 'list_all', 'search_type': 'movie',
                           'url': 'https://pasateatorrent.org/peliculas/'},
             'series': {'channel': 'pasateatorrent', 'action': 'list_all', 'search_type': 'tvshow',
                        'url': 'https://pasateatorrent.org/series_p/'}}
# DonTorrent «Series HD» (23/11/2026: 110 temporadas en 3 páginas, la mitad en 1080p; la calidad va en el nombre).
# Es más que PasateATorrent, cuyos capítulos casi nunca llegan a 1080p. La dirección es la de Balandro 4.0.34.
SERIES_HD = {'channel': 'dontorrents', 'action': 'list_all', 'search_type': 'tvshow',
             'url': 'https://dontorrent.shopping/series/hd/page/1'}
GENEROS = {'peliculas': {'channel': 'pasateatorrent', 'action': 'generos', 'search_type': 'movie'},
           'series': {'channel': 'seriespapayato', 'action': 'generos', 'search_type': 'tvshow'}}
# fila → (lista de Balandro, tipo, orden). PasateATorrent sube en castellano y por torrent (lo que mejor reproduce):
# su catálogo, en su orden, es «lo último añadido»; ordenado por fecha de estreno, los estrenos.
FILAS = {'peliculas.estrenos': (RECIENTES['peliculas'], 'peliculas', 'estreno'),
         'peliculas.recientes': (RECIENTES['peliculas'], 'peliculas', 'web'),
         'peliculas.generos': (GENEROS['peliculas'], 'peliculas', 'generos'),
         'series.novedades': (SERIES_HD, 'series', 'web'),
         'series.nuevas': (SERIES_HD, 'series', 'estreno'),
         'series.generos': (GENEROS['series'], 'series', 'generos')}


def row_url(key):
    return _encode(FILAS[key][0])


def _year(info):
    year = str((info or {}).get('year') or '')
    return year if year.isdigit() else ''


def row_item(item, kind):
    """Un elemento de una lista de Balandro (forma de filas.to_item) convertido en ficha del asistente, o None si no
    es una película o serie con id de TMDb ("Siguientes…", cabeceras)."""
    data = decode(item.get('path'))
    info = (data or {}).get('infoLabels') or {}
    if not info.get('tmdb_id'):
        return None
    tmdb = str(info['tmdb_id'])
    art = dict(item.get('art') or {})
    if art.get('thumb') and not art.get('poster'):
        art['poster'] = art['thumb']
    if kind == 'peliculas':
        title = data.get('contentTitle') or item['label']
        path, folder, props = play_url(kind, tmdb, title, _year(info), fuente=item['path']), False, {
            'IsPlayable': 'true'}
    else:
        title = data.get('contentSerieName') or item['label']
        path, folder, props = serie_url(tmdb, title, _year(info)), True, {}
    meta = dict(item.get('info') or {}, title=title, mediatype='movie' if kind == 'peliculas' else 'tvshow')
    return {'label': title, 'path': path, 'folder': folder, 'art': art, 'info': meta,
            'uniqueids': {'tmdb': tmdb}, 'properties': props}


ROW_PAGES = 3  # páginas de la web por fila: con el mínimo de 1080p se queda ~1 de cada 2 películas y 1 de 4 series


def row_kind(path):
    """'peliculas' o 'series' si path es una lista de títulos de la web (balandro.FILAS); None si no (géneros…)."""
    item = decode(path) or {}
    if item.get('action') != 'list_all':
        return None
    return {'movie': 'peliculas', 'tvshow': 'series'}.get(item.get('search_type'))


def is_next(f):
    """Si un elemento de Files.GetDirectory es el «Siguientes…» de Balandro."""
    return clean(f.get('label') or '').lower().startswith('siguiente') and decode(f.get('file')) is not None


def next_page(files):
    return next((f['file'] for f in files or [] if is_next(f)), '')


def says_hd(item):
    """Si el elemento dice él mismo que es 1080p/4K (DonTorrent lo pone en el nombre y la dirección)."""
    data = decode(item.get('path')) or {}
    return calidad.is_hd(data.get('url') or '') or calidad.is_hd(clean(item.get('label') or ''))


def needs_page(url):
    """Si la calidad de un título hay que mirarla en su página (PasateATorrent); DonTorrent la dice en el nombre."""
    return 'pasateatorrent' in (url or '')


def page_url(item):
    """La página de la web de un elemento de Balandro (forma de filas.to_item), o ''."""
    return (decode(item.get('path')) or {}).get('url') or ''


def _release(item):
    info = item.get('info') or {}
    return str(info.get('premiered') or info.get('year') or '')


# SeriesPapayaTo publica cada género dos veces, en español y en inglés (23/11/2026): se dejan los de español.
NOT_SPANISH = {'action', 'action adventure', 'animation', 'comedy', 'comedia s', 'crime', 'family', 'fantasy',
               'history', 'kids', 'mystery', 'sci fi fantasy', 'science fiction', 'soap', 'talk', 'thriller', 'war',
               'war politics'}


def genre_items(items, kind):
    """La fila «Géneros»: cada género de la web abre su lista en el asistente (?genero=)."""
    out = []
    for item in items:
        data = decode(item.get('path'))
        if not data or data.get('action') != 'list_all':
            continue
        label = clean(item.get('label', ''))
        if normalize(label) in NOT_SPANISH:
            continue
        out.append({'label': label, 'folder': True, 'art': dict(item.get('art') or {}), 'info': {'title': label},
                    'uniqueids': {}, 'properties': {},
                    'path': papa_url([('genero', kind), ('titulo', label), ('fuente', item['path'])])})
    return out


def fila(key, items):
    """Los elementos copiados de la lista de Balandro de una fila (forma de filas.to_item), como fichas del
    asistente y en el orden de la fila."""
    _, kind, order = FILAS[key]
    if order == 'generos':
        return genre_items(items, kind)
    rows = row_items(items, kind)
    if order == 'estreno':
        rows.sort(key=_release, reverse=True)
    return rows


ESTRENOS_MIN = 10  # si en enero aún hay pocos estrenos del año, se completa con los del año anterior


def year_of(item):
    year = _release(item)[:4]
    return int(year) if year.isdigit() else None


def this_year(items, year, minimum=ESTRENOS_MIN):
    """«Estrenos»: solo películas de este año (decisión del usuario, 24/11/2026; «Recién añadidas» es de cualquier
    año). Si quedan menos de minimum, se añaden las del año anterior para que la fila no salga casi vacía."""
    keep = [i for i in items if year_of(i) == year]
    if len(keep) < minimum:
        keep = [i for i in items if year_of(i) in (year, year - 1)]
    return keep


def row_items(items, kind):
    """La fila entera, sin repetidos: en series, PasateATorrent pone una entrada por temporada."""
    out, seen = [], set()
    for item in items:
        new = row_item(item, kind)
        if new and new['uniqueids']['tmdb'] not in seen:
            seen.add(new['uniqueids']['tmdb'])
            out.append(new)
    return out
