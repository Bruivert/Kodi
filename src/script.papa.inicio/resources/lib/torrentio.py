# -*- coding: utf-8 -*-
"""Torrentio: la fuente principal de películas y capítulos (desde el 23/11/2026).

Es el buscador de torrents de Stremio. Con las webs españolas Wolfmax4k y MejorTorrent y el idioma español da, para
cada película o capítulo (por su id de IMDb), los torrents con su calidad, tamaño, gente compartiendo e idioma.
Medido el 23/11/2026: estrenos y series actuales en 1080p y 4K en castellano (Reacher 4x01, Ted Lasso 4x01, Percy
Jackson 3x01…), también lo que en las webs de Balandro solo había en 720p. Solo se le dice qué título y capítulo se
busca; el torrent se ve por AllDebrid con la cuenta de la caja (plugin.py, debrid.py). Puro.
"""
from resources.lib import calidad

BASE = 'https://torrentio.strem.fun/providers=mejortorrent,wolfmax4k|language=spanish/'
SPAIN = '\U0001F1EA\U0001F1F8'  # bandera 🇪🇸 (castellano; latino sale como 🇲🇽)


def stream_url(kind, imdb, season=None, episode=None):
    if kind == 'series':
        return BASE + 'stream/series/%s:%d:%d.json' % (imdb, season or 1, episode or 1)
    return BASE + 'stream/movie/%s.json' % imdb


def _quality(stream):
    lines = (stream.get('name') or '').split('\n')
    return lines[1].strip() if len(lines) > 1 else ''


def _seeds(stream):
    title = stream.get('title') or ''
    try:
        return int(title.split('\U0001F464', 1)[1].split()[0])  # 👤 17
    except (IndexError, ValueError):
        return 0


def _rank(quality):
    q = quality.lower()
    return 0 if '1080' in q else (1 if 'hdr' not in q and 'dv' not in q else 2)  # 1080p, 4K, 4K HDR/DV


def best(streams):
    """[{btih, quality, title, seeds}] de los torrents en castellano de 1080p o más, en el orden en que probarlos:
    1080p primero (menos peso para la caja), luego 4K; en cada calidad, el que más gente comparte."""
    out = []
    for s in streams or []:
        quality = _quality(s)
        if not s.get('infoHash') or SPAIN not in (s.get('title') or '') or not calidad.is_hd(quality):
            continue
        out.append({'btih': s['infoHash'].lower(), 'quality': quality, 'seeds': _seeds(s),
                    'title': (s.get('title') or '').split('\n')[0]})
    return sorted(out, key=lambda s: (_rank(s['quality']), -s['seeds']))
