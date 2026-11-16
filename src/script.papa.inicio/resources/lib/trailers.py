# -*- coding: utf-8 -*-
"""Tráileres en español de España (nunca latino ni inglés) desde la API de TMDb. Puro: la
petición HTTP llega inyectada."""
from urllib.parse import urlencode

TMDB = 'https://api.themoviedb.org/3'


def pick_spain_trailer(videos):
    """Clave de YouTube del mejor tráiler es-ES, o None."""
    valid = [v for v in videos or []
             if v.get('site') == 'YouTube' and v.get('type') == 'Trailer'
             and v.get('iso_639_1') == 'es' and v.get('iso_3166_1') == 'ES' and v.get('key')]
    if not valid:
        return None
    best = max(valid, key=lambda v: (bool(v.get('official')), v.get('size') or 0, v.get('published_at') or ''))
    return best['key']


def _url(path, api_key, **params):
    params = dict(api_key=api_key, **params)
    return '%s%s?%s' % (TMDB, path, urlencode(params))


def videos_url(kind, tmdb_id, api_key):
    return _url('/%s/%s/videos' % (kind, tmdb_id), api_key, language='es-ES', include_video_language='es')


def find_url(imdb_id, api_key):
    return _url('/find/%s' % imdb_id, api_key, external_source='imdb_id')


def search_url(kind, title, year, api_key):
    params = {'query': title, 'language': 'es-ES'}
    if year:
        params['year' if kind == 'movie' else 'first_air_date_year'] = year
    return _url('/search/%s' % kind, api_key, **params)


def _get(http_get, url):
    try:
        return http_get(url) or {}
    except Exception:  # red caída, 401, 404, JSON roto…: sin tráiler, sin molestar
        return {}


def resolve_tmdb_id(kind, tmdb_id, imdb_id, title, year, api_key, http_get):
    if tmdb_id and str(tmdb_id).isdigit():
        return int(tmdb_id)
    results = []
    if imdb_id and str(imdb_id).startswith('tt'):
        data = _get(http_get, find_url(imdb_id, api_key))
        results = data.get('movie_results' if kind == 'movie' else 'tv_results') or []
    elif title:
        results = _get(http_get, search_url(kind, title, year, api_key)).get('results') or []
    return results[0].get('id') if results else None


def spain_trailer(kind, tmdb_id, api_key, http_get):
    return pick_spain_trailer(_get(http_get, videos_url(kind, tmdb_id, api_key)).get('results'))


def youtube_url(key):
    return 'plugin://plugin.video.youtube/play/?video_id=%s' % key
