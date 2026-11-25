# -*- coding: utf-8 -*-
"""Telegram como fuente: los vídeos del grupo (catálogo telegram.db) servidos por el addon plugin.video.telegram.

El catálogo (telegram_idx.py; carga inicial desde el Mac con tools/telegram_indexar.py) dice qué mensajes del grupo
son cada película o capítulo. El addon de Telegram, con la sesión del usuario, sirve cada mensaje en
http://127.0.0.1:8765/t<token>/stream/<grupo>/<mensaje>/video.mp4 (el token está en su addon_data y evita que otro
programa de la caja tire de la cuenta). Va detrás de Torrentio y PeLiS: arranca en ~12 s, ellos en 6–8 s; mientras
se les pregunta, se precarga el principio del vídeo (api/prefetch). Puro salvo la lectura de la base.
"""
import os
import sqlite3
from urllib.parse import urlencode

from resources.lib import telegram_idx

ADDON = 'plugin.video.telegram'
TOKEN = 'special://profile/addon_data/%s/server_token.txt' % ADDON
PORT = 8765
# «Estrenos» (solo de este año), «Recién añadidas» (de cualquier año) y «Nuevos episodios»
FILAS = {'peliculas.estrenos': 'peliculas', 'peliculas.recientes': 'peliculas', 'series.novedades': 'series'}
NEWEST = 20  # títulos del grupo que se mezclan en cada una
UPDATE_HOURS = (3, 7)  # la actualización del catálogo, de madrugada (con la caja sin usar)
PAGE = 200  # vídeos por petición a la API del addon (su máximo)
MAX_PAGES = 25  # 5.000 vídeos por noche como mucho
TRIES = 3  # versiones de un mismo título que se prueban si una no responde (borrada del grupo)


HD = ('1080p', '4K')


def has_hd(found):
    """¿El grupo tiene el título en 1080p o más? (Si no, mientras suena se prepara en AllDebrid algo mejor.)"""
    return any(v.get('quality') in HD for v in found or [])


def base(token, port=PORT):
    return 'http://127.0.0.1:%d/t%s' % (port, token)


def stream_url(base_url, peer, msg):
    return '%s/stream/%d/%d/video.mp4' % (base_url, peer, msg)


def play_target(base_url, peer, version):
    """Lo que se le da a Kodi: la dirección del vídeo, o «stack://» con todas las partes si la película está partida
    en varios vídeos (Kodi las encadena como una sola)."""
    msgs = version.get('parts') or [version['msg']]
    urls = [stream_url(base_url, peer, m) for m in msgs]
    return urls[0] if len(urls) == 1 else 'stack://' + ' , '.join(u.replace(',', ',,') for u in urls)


def prefetch_url(base_url, peer, msg):
    return '%s/api/prefetch?chat=%d&msg=%d' % (base_url, peer, msg)


def _open(path):
    if not path or not os.path.exists(path):
        return None
    return sqlite3.connect('file:%s?mode=ro' % path, uri=True)


def peer(path):
    db = _open(path)
    if not db:
        return None
    try:
        row = db.execute("SELECT valor FROM estado WHERE clave = 'grupo'").fetchone()
        return int(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        db.close()


def versions(path, kind, tmdb, season=None, episode=None):
    """Los mensajes con este título, en el orden en que probarlos (telegram_idx.rank): [{msg, quality, size}], y
    'parts' (todos los mensajes, en orden) si la película está partida en varios vídeos."""
    db = _open(path)
    if not db or not str(tmdb).isdigit():
        return []
    parts = {}
    try:
        if kind == 'series':
            rows = db.execute('SELECT msg, calidad, bytes FROM capitulos WHERE tmdb = ? AND temporada = ? AND '
                              'capitulo = ?', (int(tmdb), season or 1, episode or 1)).fetchall()
        else:
            rows = db.execute('SELECT msg, calidad, bytes FROM pelis WHERE tmdb = ?', (int(tmdb),)).fetchall()
            try:
                for msg, first in db.execute('SELECT msg, primera FROM partes WHERE primera IN (%s) ORDER BY numero'
                                             % ','.join('?' * len(rows)), [r[0] for r in rows]):
                    parts.setdefault(first, []).append(msg)
            except sqlite3.Error:
                pass  # catálogo de antes de las partes
    except sqlite3.Error:
        return []
    finally:
        db.close()
    found = sorted(({'id': m, 'msg': m, 'quality': q, 'size': b} for m, q, b in rows), key=telegram_idx.rank)
    return [dict({'msg': v['msg'], 'quality': v['quality'], 'size': v['size']},
                 **({'parts': parts[v['msg']]} if len(parts.get(v['msg'], [])) > 1 else {})) for v in found]


def newest(path, kind, limit=NEWEST, since=None):
    """Lo último que se ha subido al grupo, sin repetir título (since: solo de ese año en adelante), en la forma de
    un resultado de TMDb (lo que espera lupa.to_items: póster, fondo, sinopsis…). Los mensajes de Telegram van
    numerados por orden de subida."""
    db = _open(path)
    if not db:
        return []
    table, tipo = ('capitulos', 'series') if kind == 'series' else ('pelis', 'peliculas')
    try:
        rows = db.execute('SELECT t.tmdb, t.titulo, t.año, t.poster, t.fondo, t.sinopsis, t.nota FROM titulos t '
                          'JOIN (SELECT tmdb, MAX(msg) AS ultimo FROM %s GROUP BY tmdb) v ON v.tmdb = t.tmdb '
                          'WHERE t.tipo = ? AND t.año >= ? ORDER BY v.ultimo DESC LIMIT ?' % table,
                          (tipo, since or 0, limit)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        db.close()
    date = 'first_air_date' if kind == 'series' else 'release_date'
    name = 'name' if kind == 'series' else 'title'
    return [{'id': t, name: title, date: '%s-01-01' % year if year else '', 'poster_path': poster,
             'backdrop_path': fondo, 'overview': plot, 'vote_average': nota}
            for t, title, year, poster, fondo, plot, nota in rows]


def mix(row, extra):
    """La fila de siempre con lo nuevo del grupo intercalado (uno y uno), sin repetir títulos."""
    def tmdb(item):
        return str((item.get('uniqueids') or {}).get('tmdb') or '')
    seen = {tmdb(i) for i in row if tmdb(i)}
    extra = [i for i in extra if tmdb(i) not in seen]
    out = []
    for n in range(max(len(row), len(extra))):
        out += row[n:n + 1] + extra[n:n + 1]
    return out


def media_url(base_url, peer, cursor=None, n=PAGE):
    """Los vídeos y las fotos (carátulas) del grupo, del más nuevo al más viejo, por páginas (api/media del addon)."""
    query = [('chats', peer), ('kind', 'all'), ('n', n)] + ([('cursor', cursor)] if cursor else [])
    return '%s/api/media?%s' % (base_url, urlencode(query))


def due(now, last_day, hours=UPDATE_HOURS):
    """¿Toca actualizar? Una vez al día, de madrugada. now: time.struct_time; last_day: 'AAAA-MM-DD' o ''."""
    return hours[0] <= now.tm_hour < hours[1] and last_day != '%04d-%02d-%02d' % now[:3]


def new_videos(fetch, base_url, peer, since, max_pages=MAX_PAGES):
    """fetch(url) → JSON. Los vídeos y fotos del grupo con número de mensaje mayor que since (lo aún no catalogado)."""
    out, cursor = [], None
    for _ in range(max_pages):
        page = fetch(media_url(base_url, peer, cursor)) or {}
        items = page.get('items') or []
        fresh = [i for i in items if i.get('msg_id', 0) > since]
        out += fresh
        cursor = page.get('next')
        if len(fresh) < len(items) or not cursor:
            break
    return out
