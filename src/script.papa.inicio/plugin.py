# -*- coding: utf-8 -*-
"""Listas del asistente para las filas de la skin.

plugin://script.papa.inicio/?lista=favoritos  los favoritos de Kodi con su fanart y ficha de TMDb
plugin://script.papa.inicio/?run=<orden>      ejecuta la orden de un favorito que no es carpeta ni vídeo
"""
import json
import sys
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import favoritos as fv
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


def main(argv):
    handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip('-').isdigit() else -1
    params = {k: v[0] for k, v in parse_qs((argv[2] if len(argv) > 2 else '').lstrip('?')).items()}
    if params.get('run'):
        xbmc.executebuiltin(params['run'])
    elif params.get('lista') == 'favoritos':
        listar_favoritos(handle)
    elif handle >= 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False)


if __name__ == '__main__':
    main(sys.argv)
