# -*- coding: utf-8 -*-
"""Listas del asistente para las filas de la skin.

plugin://script.papa.inicio/?lista=favoritos  los favoritos de Kodi con su fanart y ficha de TMDb
plugin://script.papa.inicio/?run=<orden>      ejecuta la orden de un favorito que no es carpeta ni vídeo
plugin://script.papa.inicio/?fila=<lista>     una fila de Palantir desde su copia (filas.py)
plugin://script.papa.inicio/?buscar=<peliculas|series>&q=<texto>  una fila de la lupa (catalogo.py)
"""
import json
import sys
import time
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import arte_deportes
from resources.lib import catalogo
from resources.lib import favoritos as fv
from resources.lib import filas
from resources.lib import kodi_setup as ks

FAVOURITES = 'special://profile/favourites.xml'
CACHE = ks.PROFILE + 'favoritos_tmdb.json'
BASE = 'plugin://%s/' % ks.ADDON_ID


def http_get(url):
    with urlopen(Request(url, headers={'User-Agent': 'Kodi'}), timeout=5) as response:
        return json.loads(response.read().decode('utf-8'))


def _load_cache():
    try:
        return json.loads(ks.read_file(CACHE) or '{}')
    except ValueError:
        return {}


def _item(fav, info):
    li = xbmcgui.ListItem(fav['name'], offscreen=True)
    art = {'thumb': fav['thumb'], 'icon': fav['thumb'], 'poster': fav['thumb']}
    tag = li.getVideoInfoTag()
    if info:
        # Con el tipo y el id de TMDb, la skin y TMDb Helper lo tratan como las películas de Palantir (fondo, logo…).
        art['fanart'] = info['fanart']
        art['poster'] = fav['thumb'] or info['poster']
        tag.setMediaType('movie' if info['kind'] == 'movie' else 'tvshow')
        tag.setTitle(info['title'])
        if info['year']:
            tag.setYear(int(info['year']))
        tag.setPlot(info['plot'])
        tag.setUniqueIDs({'tmdb': str(info['tmdb_id'])}, 'tmdb')
        li.setProperty('tmdb_id', str(info['tmdb_id']))
    li.setArt(art)
    return li


def listar_favoritos(handle):
    cache = _load_cache()
    before = dict(cache)
    api_key = ks.setting('tmdb_key')
    for fav in fv.parse(ks.read_file(FAVOURITES)):
        info = fv.lookup(fav, api_key, http_get, cache)
        li = _item(fav, info)
        kind, path = fv.target(fav['action'])
        if kind == 'play':
            li.setProperty('IsPlayable', 'true')  # lo mismo que PlayMedia(ruta)
        elif kind == 'builtin':
            path = BASE + '?' + urlencode({'run': path})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=kind == 'folder')
    if cache != before:
        ks.write_file(CACHE, json.dumps(cache, ensure_ascii=False))
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


# Clave de filas.to_item()['info'] → método de InfoTagVideo (setInfo está obsoleto en Kodi 21).
SETTERS = {'title': ('setTitle', str), 'year': ('setYear', int), 'plot': ('setPlot', str),
           'rating': ('setRating', float), 'votes': ('setVotes', int), 'genre': ('setGenres', list),
           'duration': ('setDuration', int), 'mpaa': ('setMpaa', str), 'premiered': ('setPremiered', str),
           'studio': ('setStudios', list), 'country': ('setCountries', list), 'tagline': ('setTagLine', str),
           'originaltitle': ('setOriginalTitle', str), 'imdbnumber': ('setIMDBNumber', str),
           'tvshowtitle': ('setTvShowTitle', str), 'season': ('setSeason', int), 'episode': ('setEpisode', int),
           'trailer': ('setTrailer', str), 'director': ('setDirectors', list), 'mediatype': ('setMediaType', str)}


def _as(kind, value):
    if kind is list:
        return list(value) if isinstance(value, (list, tuple)) else [str(value)]
    try:
        return kind(value)
    except (TypeError, ValueError):
        return None


def _fila_item(item):
    li = xbmcgui.ListItem(item['label'], offscreen=True)
    li.setArt(item['art'])
    tag = li.getVideoInfoTag()
    for key, value in item['info'].items():
        name, kind = SETTERS.get(key, (None, None))
        value = _as(kind, value) if name else None
        if value is not None:
            getattr(tag, name)(value)
    if item['uniqueids']:
        default = 'tmdb' if 'tmdb' in item['uniqueids'] else next(iter(item['uniqueids']))
        tag.setUniqueIDs(item['uniqueids'], default)
    for name, value in item['properties'].items():
        li.setProperty(name, str(value))
    return li


def listar_fila(handle, key):
    path = filas.row_paths(ks.load_rutas()).get(key)
    cached = ks.load_fila(key)
    if path and not filas.usable(cached, path):
        files = ks.fetch_row(path)  # primera vez (o la lista cambió): se pide ahora y se guarda
        if filas.keeps(files, key):
            cached = filas.entry(path, files, time.time())
            ks.save_fila(key, cached)
    items = (cached or {}).get('items') or []
    if key.startswith('deportes.'):  # BlackGhost no trae fondos: los de TheSportsDB
        items = arte_deportes.apply(items, key, ks.load_arte())
    for item in items:
        xbmcplugin.addDirectoryItem(handle, item['path'], _fila_item(item), isFolder=item['folder'])
    xbmcplugin.setContent(handle, filas.content(items))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def listar_busqueda(handle, kind, text):
    """Una fila de la búsqueda de la skin, sacada del catálogo de Palantir sin arrancarlo."""
    start = time.time()
    items = catalogo.find(ks.palantir_db(), xbmcvfs.translatePath(ks.CATALOGO), kind, text)
    for item in items:
        xbmcplugin.addDirectoryItem(handle, item['path'], _fila_item(item), isFolder=item['folder'])
    xbmcplugin.setContent(handle, filas.content(items))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    ks.log('buscar %s %r: %d en %.2fs' % (kind, text, len(items), time.time() - start))


def main(argv):
    handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip('-').isdigit() else -1
    params = {k: v[0] for k, v in parse_qs((argv[2] if len(argv) > 2 else '').lstrip('?')).items()}
    if params.get('run'):
        xbmc.executebuiltin(params['run'])
    elif params.get('lista') == 'favoritos':
        listar_favoritos(handle)
    elif params.get('buscar'):
        listar_busqueda(handle, params['buscar'], params.get('q', ''))
    elif params.get('fila'):
        listar_fila(handle, params['fila'])
    elif handle >= 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False)


if __name__ == '__main__':
    main(sys.argv)
