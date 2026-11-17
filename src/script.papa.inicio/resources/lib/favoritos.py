# -*- coding: utf-8 -*-
"""Los favoritos de Kodi con su ficha de TMDb (fanart, sinopsis, id), para que la skin los pinte como las películas
de Palantir. Kodi solo guarda de cada favorito el nombre, la miniatura y la orden que lo abre. Puro: las peticiones
HTTP llegan inyectadas."""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from resources.lib.discover import clean, normalize

TMDB = 'https://api.themoviedb.org/3'
IMAGES = 'https://image.tmdb.org/t/p'
YEAR = re.compile(r'\((\d{4})\)')


def parse(xml_text):
    """[{'name', 'thumb', 'action'}] de favourites.xml, en su orden."""
    try:
        root = ET.fromstring(xml_text or '')
    except ET.ParseError:
        return []
    return [{'name': f.get('name', ''), 'thumb': f.get('thumb', ''), 'action': (f.text or '').strip()}
            for f in root.iter('favourite')]


def title_year(name):
    """('The Hack', '2025') de "* The Hack (2025) [Esp, Eng]" (así los guarda Palantir)."""
    text = clean(name)
    found = YEAR.search(text)
    title = text[:found.start()] if found else text
    title = re.sub(r'\[[^\]]*\]', ' ', title).strip(' *')
    return ' '.join(title.split()), found.group(1) if found else ''


def target(action):
    """('folder', ruta) si abre una carpeta, ('play', ruta) si reproduce, ('builtin', orden) para lo demás."""
    found = re.match(r'^ActivateWindow\(\s*[^,]+,\s*"([^"]+)"', action or '')
    if found:
        return 'folder', found.group(1)
    found = re.match(r'^PlayMedia\(\s*"([^"]+)"', action or '')
    if found:
        return 'play', found.group(1)
    return 'builtin', action


def hint(action):
    """Palantir reproduce las películas y abre carpeta (temporadas) para las series."""
    return 'movie' if target(action)[0] == 'play' else 'tv'


def search_url(title, api_key):
    return '%s/search/multi?%s' % (TMDB, urlencode({'query': title, 'language': 'es-ES', 'api_key': api_key}))


def _image(size, path):
    return '%s/%s%s' % (IMAGES, size, path) if path else ''


def pick(results, title, year, kind_hint):
    """La película o serie de la búsqueda con este título: primero la de su año, luego la del tipo que se espera."""
    wanted = normalize(title)
    found = []
    for r in results or []:
        kind = r.get('media_type')
        if kind not in ('movie', 'tv'):
            continue
        names = (r.get('title'), r.get('original_title')) if kind == 'movie' else (r.get('name'), r.get('original_name'))
        if wanted not in [normalize(n) for n in names if n]:
            continue
        found.append(r)
    if not found:
        return None

    def score(r):
        r_year = (r.get('release_date') or r.get('first_air_date') or '')[:4]
        return (bool(year) and r_year == year, r.get('media_type') == kind_hint)
    best = max(found, key=score)  # max devuelve el primero de los empatados: el orden de TMDb
    kind = best['media_type']
    return {'kind': kind, 'tmdb_id': best['id'], 'title': best.get('title') or best.get('name'),
            'year': (best.get('release_date') or best.get('first_air_date') or '')[:4],
            'plot': best.get('overview', ''), 'fanart': _image('w1280', best.get('backdrop_path')),
            'poster': _image('w500', best.get('poster_path'))}


def lookup(fav, api_key, http_get, cache):
    """La ficha de TMDb de un favorito con año (película o serie de Palantir), o None. Se guarda en cache, también
    "no está en TMDb"; un fallo de red no, para volver a intentarlo."""
    title, year = title_year(fav['name'])
    if not (year and api_key):
        return None
    key = '%s|%s' % (title, year)
    if key in cache:
        return cache[key]
    try:
        results = (http_get(search_url(title, api_key)) or {}).get('results')
    except Exception:
        return None
    cache[key] = pick(results, title, year, hint(fav['action']))
    return cache[key]
