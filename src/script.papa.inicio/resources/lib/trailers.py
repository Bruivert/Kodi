# -*- coding: utf-8 -*-
"""Tráileres en español de España (nunca latino ni inglés): los de TMDb y, si no tiene uno bueno, el que encuentre
la búsqueda de YouTube. Puro: las peticiones HTTP llegan inyectadas."""
import re
import unicodedata
from urllib.parse import urlencode

from resources.lib.discover import normalize

TMDB = 'https://api.themoviedb.org/3'
OEMBED = 'https://www.youtube.com/oembed'
# La búsqueda de la web de YouTube, sin clave. "EgIQAQ==" pide solo vídeos (ni canales ni listas).
SEARCH = 'https://www.youtube.com/youtubei/v1/search?prettyPrint=false'
SEARCH_CLIENT = {'clientName': 'WEB', 'clientVersion': '2.20250101.00.00', 'hl': 'es', 'gl': 'ES'}
SEARCH_ONLY_VIDEOS = 'EgIQAQ%3D%3D'

# TMDb a veces marca como es-ES vídeos que se oyen en inglés: subtitulados, o directamente mal etiquetados (para
# "Enfrentados: Marfil" da "Drawn Together - Official Teaser | Prime Video Canada"). Se mira también el título.
SUBTITLED = ('subtitulad', 'vose', 'v.o.s', 'version original')
ENGLISH = ('official',)
SPANISH = ('espanol', 'castellano', 'doblad', 'oficial')  # "oficial" no está dentro de "official"


def _plain(text):
    return unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('ascii').lower()


def looks_english(title):
    """Por el título: subtitulado (se oye el original) o en inglés sin ninguna marca de español."""
    text = _plain(title)
    if any(m in text for m in SUBTITLED):
        return True
    return any(m in text for m in ENGLISH) and not any(m in text for m in SPANISH)


def spain_trailers(videos, vtype='Trailer'):
    """Tráileres (o teasers) es-ES de YouTube, del mejor al peor."""
    valid = [v for v in videos or []
             if v.get('site') == 'YouTube' and v.get('type') == vtype
             and v.get('iso_639_1') == 'es' and v.get('iso_3166_1') == 'ES' and v.get('key')]
    return sorted(valid, key=lambda v: (bool(v.get('official')), v.get('size') or 0, v.get('published_at') or ''),
                  reverse=True)


def pick_spain_trailer(videos):
    """Clave de YouTube del mejor tráiler es-ES, o None."""
    found = spain_trailers(videos)
    return found[0]['key'] if found else None


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


def oembed_url(key):
    return '%s?%s' % (OEMBED, urlencode({'url': 'https://www.youtube.com/watch?v=%s' % key, 'format': 'json'}))


def details_url(kind, tmdb_id, api_key):
    return _url('/%s/%s' % (kind, tmdb_id), api_key, language='es-ES')


def _first_spanish(candidates, http_get):
    for video in candidates:
        if looks_english(video.get('name')):
            continue  # TMDb ya dice que es subtitulado
        # Si YouTube no contesta no se puede comprobar: vale la elección de TMDb (y no se guarda en caché).
        title = _get(http_get, oembed_url(video['key'])).get('title')
        if title and looks_english(title):
            continue
        return video['key']
    return None


def spain_trailer(kind, tmdb_id, api_key, http_get):
    return _first_spanish(spain_trailers(_get(http_get, videos_url(kind, tmdb_id, api_key)).get('results')), http_get)


# --- Búsqueda en YouTube, para lo que TMDb no tiene (la mayoría de los estrenos) ---

MAX_SECONDS = 5 * 60  # más largo ya no es un tráiler (películas completas, resúmenes, reacciones)
FROM_SPAIN = ('espanol', 'castellano', 'espana', 'spain', 'doblad')
LATIN = ('latino', 'latam', 'mexico', 'argentina', 'colombia')
YEAR = re.compile(r'\b(?:19|20)\d\d\b')


def seconds(length):
    parts = (length or '').split(':')
    if not all(p.isdigit() for p in parts):
        return None
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total


def _runs(text):
    return ''.join(run.get('text', '') for run in (text or {}).get('runs') or [])


def search_results(data):
    """Vídeos de una respuesta de la búsqueda de YouTube, en su orden."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            video = node.get('videoRenderer')
            if isinstance(video, dict) and video.get('videoId'):
                found.append({'key': video['videoId'], 'title': _runs(video.get('title')),
                              'channel': _runs(video.get('ownerText')),
                              'seconds': seconds((video.get('lengthText') or {}).get('simpleText'))})
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(data)
    return found


def good_search_result(video, kind, title, year):
    """Es el tráiler de esta película o serie, doblado al español de España."""
    name, film = ' %s ' % normalize(video['title']), ' %s ' % normalize(title)
    rest = name.replace(film, ' ')  # lo que dice el vídeo aparte del título ("1917", "Narcos: México")
    text = _plain('%s %s' % (rest, video['channel']))
    # El vídeo empieza por el título, sin subtítulo detrás: "The Running Man" o "Bob Esponja: Un héroe fuera del
    # agua" son otras obras.
    if not film.strip() or not name.startswith(film) or not any(w in rest.split() for w in ('trailer', 'teaser')):
        return False
    after = _plain(video['title']).partition(_plain(title).strip())[2]
    if after.lstrip().startswith(':'):
        return False
    if not video['seconds'] or video['seconds'] > MAX_SECONDS:
        return False
    if looks_english(video['title']) or any(m in text for m in LATIN) or not any(m in text for m in FROM_SPAIN):
        return False
    # Otra película con el mismo título; en series cada temporada lleva su año.
    return not (kind == 'movie' and str(year).isdigit()
                and any(abs(int(y) - int(year)) > 1 for y in YEAR.findall(rest)))


def search_query(kind, title, year):
    if kind == 'tv':
        return '%s serie tráiler español' % title
    return ('%s %s tráiler español' % (title, year)) if year else ('%s tráiler español' % title)


def youtube_trailer(kind, title, year, http_post):
    payload = {'context': {'client': dict(SEARCH_CLIENT)}, 'query': search_query(kind, title, year),
               'params': SEARCH_ONLY_VIDEOS}
    try:
        data = http_post(SEARCH, payload)
    except Exception:
        return None
    good = [v for v in search_results(data) if good_search_result(v, kind, title, year)]
    # Primero los canales españoles (las distribuidoras: "Amazon Prime Video España"), luego el orden de YouTube.
    good.sort(key=lambda v: not any(m in _plain(v['channel']) for m in ('espana', 'spain')))
    return good[0]['key'] if good else None


# --- Si no hay nada en castellano: como la web de TMDb, el vídeo en el idioma original (o en inglés) ---

ORIGINAL_TYPES = ('Trailer', 'Teaser', 'Clip')


def original_videos_url(kind, tmdb_id, original_language, api_key):
    return _url('/%s/%s/videos' % (kind, tmdb_id), api_key,
                include_video_language='%s,en,null' % (original_language or 'en'))


def pick_original_trailer(videos, original_language):
    """Clave del mejor vídeo de TMDb en cualquier idioma: tráiler, si no teaser, si no clip; el idioma original
    antes que el inglés."""
    valid = [v for v in videos or [] if v.get('site') == 'YouTube' and v.get('key') and v.get('type') in ORIGINAL_TYPES]
    if not valid:
        return None
    return max(valid, key=lambda v: (-ORIGINAL_TYPES.index(v['type']), v.get('iso_639_1') == original_language,
                                     bool(v.get('official')), v.get('size') or 0, v.get('published_at') or ''))['key']


def find_trailer(kind, tmdb_id, api_key, http_get, http_post):
    """El tráiler de TMDb; si no tiene uno bueno, el de la búsqueda de YouTube; si tampoco, el teaser de TMDb; y si
    no hay nada en castellano, el vídeo de TMDb en el idioma original."""
    answer = _get(http_get, videos_url(kind, tmdb_id, api_key))
    videos = answer.get('results')
    key = _first_spanish(spain_trailers(videos), http_get)
    if key:
        return key
    info = _get(http_get, details_url(kind, tmdb_id, api_key))
    title = info.get('title') or info.get('name')
    year = (info.get('release_date') or info.get('first_air_date') or '')[:4]
    if title:
        key = youtube_trailer(kind, title, year, http_post)
    key = key or _first_spanish(spain_trailers(videos, 'Teaser'), http_get)
    if key or not info or 'results' not in answer:  # sin saber qué hay en castellano no se pone otro idioma
        return key
    language = info.get('original_language')
    return pick_original_trailer(_get(http_get, original_videos_url(kind, tmdb_id, language, api_key)).get('results'),
                                 language)


def youtube_url(key):
    return 'plugin://plugin.video.youtube/play/?video_id=%s' % key
