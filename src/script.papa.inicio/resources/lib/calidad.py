# -*- coding: utf-8 -*-
"""Mínimo 1080p: nada por debajo (decisión del usuario, 23/11/2026).

Películas: PasateATorrent dice la calidad de cada una en su página (720p, 1080p, 4K…); se lee con el mismo patrón que
usa Balandro (channels/pasateatorrent.py, findvideos). Lo que no dice calidad no vale.
Capítulos: las webs en castellano no dicen la calidad, solo el tamaño; se deduce de él y de la duración del capítulo
(TMDb): un 1080p ocupa al menos GB_PER_HOUR por hora. Puro.
"""
import re

HD = re.compile(r'1080|2160|\b4k\b|uhd|full ?hd', re.I)
GB_PER_HOUR = 1.6  # 45 min → 1,2 GB. Un 720p de 45 min ronda 0,6 GB; un 1080p, de 1,2 GB en adelante
DEFAULT_MINUTES = 45
_PASATE_ROWS = re.compile(r'<tbody.*?</td>.*?</td>.*?<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300">'
                          r'(.*?)</td>', re.S)
_PASATE_LINKS = re.compile(r'<tbody.*?</td>.*?</td>.*?<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300">'
                           r'(.*?)</td>.*?<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300 text-center">'
                           r'(.*?)</td>.*?href="(.*?)"', re.S)
PASATE = 'https://pasateatorrent.org'

_PASATE_EPISODES = re.compile(r'<tr wire:key=episode-0>.*?<td class="px-6 py-4 whitespace-nowrap text-sm '
                              r'text-neutral-300">.*?</td>.*?<td class="px-6 py-4 whitespace-nowrap text-sm '
                              r'text-neutral-300 text-center">(.*?)</td>', re.S)
MAX_AGE = 3 * 86400  # s: lo mirado de una página vale tres días (la web puede subir otra calidad)
_SIZE = re.compile(r'([\d.,]+)\s*(GB|MB|G|M)\b', re.I)


def is_hd(quality):
    return bool(quality and HD.search(quality))


def pasate_qualities(html):
    """Las calidades de la página de una película de PasateATorrent ([] si no hay o cambió la web)."""
    text = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', html or '')
    return [q.strip() for q in _PASATE_ROWS.findall(text)]


def pasate_links(html):
    """[(calidad, url del .torrent)] de la página de una película de PasateATorrent (el patrón de Balandro)."""
    text = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', html or '')
    return [(q.strip(), url if url.startswith('http') else PASATE + url) for q, _, url in _PASATE_LINKS.findall(text)]


def pasate_sizes(html):
    """Los tamaños de los capítulos de la página de una temporada de PasateATorrent (como episodios de Balandro)."""
    text = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', html or '')
    return [s.strip() for s in _PASATE_EPISODES.findall(text)]


def any_hd(qualities):
    return any(is_hd(q) for q in qualities or [])


def size_gb(text):
    """'0.67GB' → 0.67, '700 MB' → 0.7; None si no es un tamaño."""
    found = _SIZE.search(text or '')
    if not found:
        return None
    value = float(found.group(1).replace(',', '.'))
    return value if found.group(2).upper().startswith('G') else value / 1000


def episode_hd(size_text, minutes=None):
    """Si un capítulo de ese tamaño y duración (minutos, de TMDb) es 1080p. Sin tamaño, no vale."""
    gb = size_gb(size_text)
    if gb is None:
        return False
    return gb >= GB_PER_HOUR * (minutes or DEFAULT_MINUTES) / 60.0


def fresh(entry, now):
    return bool(entry) and now - entry.get('time', 0) < MAX_AGE


def page_entry(kind, html, now):
    """Lo que se guarda de una página: sus calidades (película) o los tamaños de sus capítulos (serie)."""
    if kind == 'peliculas':
        return {'time': now, 'q': pasate_qualities(html), 'links': pasate_links(html)}
    return {'time': now, 'q': pasate_sizes(html)}


def page_ok(kind, entry):
    """Si la página tiene algo en 1080p o más. Sin mirar todavía, no (nada por debajo de 1080p)."""
    if not entry:
        return False
    if kind == 'peliculas':
        return any_hd(entry.get('q'))
    return any(episode_hd(size) for size in entry.get('q') or [])
