# -*- coding: utf-8 -*-
"""Temporadas y capítulos de una serie, sacados de Balandro y con el arte de TMDb.

Cada web de Balandro lista a su manera: unas dan temporadas y luego capítulos, otras (con una sola temporada) los
capítulos directamente, y algunas los paginan con «Siguientes…». El número de temporada y capítulo viene en
contentSeason/contentEpisodeNumber, pero no siempre (SeriesPapayaTo tiene una errata, «ontentSeason»): entonces se lee
del texto («Temporada 2», «2x05»). Puro: las listas y las fichas de TMDb llegan de fuera.
"""
import re
from urllib import parse

from resources.lib import balandro
from resources.lib import calidad
from resources.lib.discover import clean
from resources.lib.fichas import papa_url, play_url

TMDB = 'https://api.themoviedb.org/3/'
IMAGES = 'https://image.tmdb.org/t/p/'
SEASON_RE = re.compile(r'\btemp(?:orada|\.)?\s*(\d+)|\b(\d+)\s*[ªºa]?\s*temp', re.I)  # «Temporada 2», «2ª Temp.»
EPISODE_RE = re.compile(r'\b(\d{1,2})x(\d{1,3})\b')


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_listing(files):
    """{'seasons': [{'season', 'path'}], 'episodes': [{'season', 'episode', 'path'}], 'next': ruta o ''} de una
    lista de Balandro (Files.GetDirectory)."""
    out = {'seasons': [], 'episodes': [], 'next': ''}
    for f in files or []:
        item = balandro.decode(f.get('file'))
        if not item:
            continue
        label = clean(f.get('label') or item.get('title') or '')
        action = item.get('action')
        if label.lower().startswith('siguiente'):
            out['next'] = f['file']
            continue
        if action == 'findvideos':
            pair = EPISODE_RE.search(label)
            season = _int(item.get('contentSeason')) or (pair and int(pair.group(1)))
            episode = _int(item.get('contentEpisodeNumber')) or (pair and int(pair.group(2)))
            if season is not None and episode is not None and season != 99:  # 99: «temporada completa» en un torrent
                # PasateATorrent pone en quality el tamaño del capítulo («0.67GB»): sirve para su calidad (calidad.py)
                out['episodes'].append({'season': season, 'episode': episode, 'path': f['file'],
                                        'size': str(item.get('quality') or '')})
        elif action in ('episodios', 'temporadas'):
            found = SEASON_RE.search(label)
            season = _int(item.get('contentSeason')) or (found and int(found.group(1) or found.group(2)))
            if season is not None:
                out['seasons'].append({'season': season, 'path': f['file']})
    seen = set()
    out['seasons'] = [s for s in sorted(out['seasons'], key=lambda s: s['season'])
                      if not (s['season'] in seen or seen.add(s['season']))]
    seen = set()
    out['episodes'] = [e for e in sorted(out['episodes'], key=lambda e: (e['season'], e['episode']))
                       if not ((e['season'], e['episode']) in seen or seen.add((e['season'], e['episode'])))]
    return out


def seasons_from_sources(found):
    """Temporadas de una serie cuando la web tiene una página por temporada (PasateATorrent «Reacher Temporada 3»,
    DonTorrent «La playlist - 1ª Temporada [720p]»), sacadas de los resultados de la búsqueda sin abrir ninguna. Sin
    número: la 1. 'hd': la página dice 1080p o 4K (DonTorrent); si no lo dice, se mira el tamaño de cada capítulo.
    DonTorrent tiene versiones sin calidad (SD) y [720p]: de esas temporadas solo vale la marcada en 1080p/4K."""
    seasons = {}
    for s in found:
        text = clean(s.get('label') or '')
        number = SEASON_RE.search(text)
        n = int(number.group(1) or number.group(2)) if number else 1
        hd = calidad.is_hd(text) or calidad.is_hd(s.get('url') or '')
        if s.get('channel') == 'dontorrents' and not hd:
            continue
        if n not in seasons or (hd and not seasons[n]['hd']):
            seasons[n] = {'season': n, 'path': s['path'], 'hd': hd}
    return [seasons[n] for n in sorted(seasons)]


def runtime(show, season_tmdb, episode):
    """Minutos de un capítulo según TMDb (el suyo, o el típico de la serie); None si no se sabe."""
    for ep in (season_tmdb or {}).get('episodes') or []:
        if ep.get('episode_number') == episode and ep.get('runtime'):
            return ep['runtime']
    typical = (show or {}).get('episode_run_time') or []
    return typical[0] if typical else None


TMDB_SOURCE = 'tmdb'  # temporada que se lista con los capítulos de TMDb (cada uno se busca al pulsarlo)


def tmdb_seasons(show, today):
    """Temporadas ya estrenadas según TMDb ([{season, path, hd}]), sin la 0 (especiales)."""
    out = []
    for s in (show or {}).get('seasons') or []:
        n, aired = s.get('season_number'), s.get('air_date') or ''
        if n and s.get('episode_count') and aired and aired <= today:
            out.append({'season': n, 'path': TMDB_SOURCE, 'hd': True})
    return sorted(out, key=lambda s: s['season'])


def tmdb_episodes(season_tmdb, season, today):
    """Capítulos ya emitidos de una temporada según TMDb ([{season, episode, path}])."""
    return [{'season': season, 'episode': e['episode_number'], 'path': ''}
            for e in (season_tmdb or {}).get('episodes') or []
            if e.get('episode_number') and (e.get('air_date') or '9999') <= today]


def find_episode(episodes, season, episode):
    for e in episodes:
        if e['season'] == season and e['episode'] == episode:
            return e['path']
    return None


def temporada_url(tmdb, title, year, season, fuente, hd=False):
    return papa_url([('temporada', season), ('tmdb', tmdb), ('titulo', title), ('anio', year), ('fuente', fuente),
                     ('hd', 1 if hd else None)])


def show_url(tmdb, key):
    return TMDB + 'tv/%s?%s' % (tmdb, parse.urlencode({'api_key': key, 'language': 'es-ES'}))


def season_url(tmdb, season, key):
    return TMDB + 'tv/%s/season/%s?%s' % (tmdb, season, parse.urlencode({'api_key': key, 'language': 'es-ES'}))


def _image(size, path):
    return IMAGES + size + path if path else ''


def show_art(show):
    """Póster y fondo de la serie (ficha de TMDb tv/<id>)."""
    show = show or {}
    art = {'poster': _image('w500', show.get('poster_path')), 'fanart': _image('w1280', show.get('backdrop_path'))}
    art['thumb'] = art['poster']
    return {k: v for k, v in art.items() if v}


def season_items(tmdb, title, year, seasons, show):
    """Temporadas como carpetas del asistente, con el póster de cada una si TMDb lo tiene."""
    base = show_art(show)
    posters = {s.get('season_number'): s for s in (show or {}).get('seasons') or []}
    items = []
    for s in seasons:
        meta = posters.get(s['season']) or {}
        art = dict(base)
        if meta.get('poster_path'):
            art['poster'] = art['thumb'] = _image('w500', meta['poster_path'])
        info = {'title': 'Temporada %d' % s['season'], 'tvshowtitle': title, 'season': s['season'],
                'mediatype': 'season', 'plot': meta.get('overview') or (show or {}).get('overview')}
        items.append({'label': info['title'], 'folder': True, 'art': art, 'uniqueids': {'tmdb': str(tmdb)},
                      'path': temporada_url(tmdb, title, year, s['season'], s['path'], s.get('hd')),
                      'properties': {},
                      'info': {k: v for k, v in info.items() if v not in (None, '')}})
    return items


def episode_items(tmdb, title, year, episodes, show, seasons_tmdb):
    """Capítulos reproducibles con su foto, título y resumen de TMDb. seasons_tmdb: {temporada: ficha de TMDb}."""
    base = show_art(show)
    items = []
    for e in episodes:
        meta = {ep.get('episode_number'): ep for ep in (seasons_tmdb.get(e['season']) or {}).get('episodes') or []}
        ep = meta.get(e['episode']) or {}
        name = ep.get('name') or 'Capítulo %d' % e['episode']
        art = dict(base)
        if ep.get('still_path'):
            art['thumb'] = _image('w780', ep['still_path'])
        info = {'title': name, 'tvshowtitle': title, 'season': e['season'], 'episode': e['episode'],
                'mediatype': 'episode', 'plot': ep.get('overview'), 'premiered': ep.get('air_date'),
                'duration': (ep.get('runtime') or 0) * 60 or None, 'rating': ep.get('vote_average') or None}
        items.append({'label': '%d. %s' % (e['episode'], name), 'folder': False, 'art': art,
                      'path': play_url('series', tmdb, title, year, e['season'], e['episode'], fuente=e['path']),
                      'info': {k: v for k, v in info.items() if v not in (None, '')},
                      'uniqueids': {'tmdb': str(tmdb)}, 'properties': {'IsPlayable': 'true'}})
    return items
