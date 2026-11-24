# -*- coding: utf-8 -*-
"""PeLiS (pelis-addon.com): addon de Stremio en castellano con AllDebrid, lo más parecido a Palantir (24/11/2026).

Tiene lo antiguo (Torrente 1998, La que se avecina, Los Serrano…) y lo nuevo (Tony 2026, Reacher 4x01), en servidores
de descarga y torrents, ya preparados en AllDebrid (⚡). La dirección personal del usuario (pelis-addon.com/<config>,
con su clave de AllDebrid cifrada) se pega en la página de la caja (pegar.py) y se guarda en un ajuste oculto: nunca
se escribe en el log. Cada enlace es una dirección de PeLiS que redirige al vídeo de AllDebrid. Puro.
"""
import re

from resources.lib import calidad

_SIZE = re.compile(r'\U0001F4BE\s*([\d.,]+)\s*(GB|MB)', re.I)  # 💾 19.27 GB
_AUDIO = re.compile(r'\U0001F50A([^\U0001F4BE\U0001F9F2\U0001F4C4\n]*)')  # 🔊 Español - Inglés


def stream_url(base, kind, imdb, season=None, episode=None):
    if kind == 'series':
        return '%s/stream/series/%s:%d:%d.json' % (base, imdb, season or 1, episode or 1)
    return '%s/stream/movie/%s.json' % (base, imdb)


def _size(text):
    found = _SIZE.search(text or '')
    if not found:
        return None
    value = float(found.group(1).replace(',', '.'))
    return value if found.group(2).upper() == 'GB' else value / 1000


def _rank(quality):
    q = quality.lower()
    if 'dolby' in q or 'dv' in q.split():
        return 3
    if '4k' in q or '2160' in q:
        return 2 if 'hdr' in q else 1
    return 0


def best(streams):
    """Los enlaces de PeLiS que valen, en el orden en que probarlos: ya preparados en AllDebrid (⚡), con castellano
    («Español»; «Latino» solo no vale), de 1080p o más; 1080p primero, luego 4K, Dolby Vision al final; en cada
    calidad, el fichero más ligero (va más fluido por la Wi-Fi). [{url, quality, size}]"""
    out = []
    for s in streams or []:
        name = (s.get('name') or '').replace('\n', ' ')
        text = s.get('title') or s.get('description') or ''
        audio = (_AUDIO.search(text) or [None, ''])[1]
        quality = name.split('⚡', 1)[-1].strip()  # «AD ⚡ 1080p» → «1080p»
        if '⚡' not in name or not s.get('url') or 'espa' not in audio.lower() or not calidad.is_hd(quality):
            continue
        out.append({'url': s['url'], 'quality': quality, 'size': _size(text)})
    return sorted(out, key=lambda s: (_rank(s['quality']), s['size'] if s['size'] is not None else 999))
