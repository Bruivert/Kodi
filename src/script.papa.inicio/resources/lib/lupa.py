# -*- coding: utf-8 -*-
"""La búsqueda de la skin (la lupa) en TMDb: siempre al día, como el buscador de Balandro.

El catálogo de Palantir (catalogo.py) dejó de actualizarse cuando Palantir cerró; TMDb contesta en ~0,5 s y trae el
póster y el fondo. Al pulsar, la película se reproduce y la serie abre sus temporadas, por Balandro (fichas.py); si
Balandro no la tiene, avisa. Puro: la respuesta de TMDb llega de fuera.
"""
from urllib import parse

from resources.lib.fichas import play_url, serie_url

TMDB = 'https://api.themoviedb.org/3/'
IMAGES = 'https://image.tmdb.org/t/p/'
TYPES = {'peliculas': 'movie', 'series': 'tv'}
ALL = 'todo'  # películas y luego series: AF3 pone una fila por tipo
MIN_CHARS = 2
LIMIT = 20


def kinds(kind):
    return list(TYPES) if kind == ALL else [kind] if kind in TYPES else []


def search_url(kind, text, key):
    return TMDB + 'search/%s?%s' % (TYPES[kind], parse.urlencode({
        'api_key': key, 'language': 'es-ES', 'region': 'ES', 'include_adult': 'false', 'query': text}))


def to_items(kind, results, limit=LIMIT):
    """Los resultados con póster (sin él suelen ser fichas vacías), como elementos de fila."""
    movie = kind == 'peliculas'
    items = []
    for r in results or []:
        if not r.get('poster_path') or not r.get('id'):
            continue
        title = r.get('title' if movie else 'name') or ''
        date = r.get('release_date' if movie else 'first_air_date') or ''
        year = date[:4] if date[:4].isdigit() else ''
        art = {'poster': IMAGES + 'w500' + r['poster_path']}
        art['thumb'] = art['poster']
        if r.get('backdrop_path'):
            art['fanart'] = IMAGES + 'w1280' + r['backdrop_path']
        info = {'title': title, 'mediatype': 'movie' if movie else 'tvshow', 'plot': r.get('overview'),
                'rating': r.get('vote_average') or None, 'premiered': date or None,
                'year': int(year) if year else None}
        items.append({'label': title, 'folder': not movie, 'art': art,
                      'path': play_url(kind, r['id'], title, year) if movie else serie_url(r['id'], title, year),
                      'info': {k: v for k, v in info.items() if v not in (None, '')},
                      'uniqueids': {'tmdb': str(r['id'])}, 'properties': {'IsPlayable': 'true'} if movie else {}})
        if len(items) == limit:
            break
    return items
