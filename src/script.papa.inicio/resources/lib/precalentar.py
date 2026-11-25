# -*- coding: utf-8 -*-
"""Lo de las filas, preparado de antemano en AllDebrid (como iba Palantir: al pulsar, arranca al momento).

Crítica del 25/11/2026: Palantir era rápido porque sus películas ya estaban en un servidor y AllDebrid las daba al
instante; aquí cada pulsación empezaba de cero. Cada madrugada, para lo que sale en «Estrenos», «Recién añadidas» y
el último capítulo de las series de «Nuevos episodios», se pide a AllDebrid el mejor torrent en castellano de
Torrentio (magnet/upload). Si AllDebrid ya lo tenía, se quita de la lista al momento (no deja rastro); si no, lo
descarga a su nube y al día siguiente arranca en segundos. Lo preparado se quita de la lista a las dos semanas. Puro.
"""
MAX_PER_NIGHT = 40  # títulos por noche, como mucho
AGAIN_AFTER = 7 * 86400  # un título ya preparado no se vuelve a pedir hasta dentro de una semana
KEEP = 14 * 86400  # lo que AllDebrid descargó por esto se quita de la lista a las dos semanas


def targets(movies, shows, limit=MAX_PER_NIGHT):
    """[(kind, tmdb, temporada, capítulo)] sin repetir, en el orden de las filas: primero las películas (los estrenos
    van delante), luego el último capítulo emitido de cada serie. movies: [tmdb]; shows: [(tmdb, temporada, cap)]."""
    out, seen = [], set()
    for tmdb in movies:
        key = ('peliculas', str(tmdb), None, None)
        if str(tmdb).isdigit() and key not in seen:
            seen.add(key)
            out.append(key)
    for tmdb, season, episode in shows:
        key = ('series', str(tmdb), season, episode)
        if str(tmdb).isdigit() and season and episode and key not in seen:
            seen.add(key)
            out.append(key)
    return out[:limit]


def key(target):
    kind, tmdb, season, episode = target
    return '%s:%s:%s:%s' % (kind, tmdb, season or '', episode or '')


def due(record, target, now):
    """¿Toca pedirlo? record: {clave: {'time': …}} de lo ya pedido."""
    done = record.get(key(target))
    return not done or now - done.get('time', 0) >= AGAIN_AFTER


def last_episode(show):
    """(temporada, capítulo) del último capítulo emitido según la ficha de TMDb de la serie, o None."""
    last = (show or {}).get('last_episode_to_air') or {}
    if last.get('season_number') and last.get('episode_number'):
        return last['season_number'], last['episode_number']
    return None


def to_delete(record, now):
    """Los id de AllDebrid de lo descargado por esto hace más de KEEP (se quitan de la lista de la cuenta)."""
    return [v['id'] for v in record.values() if v.get('id') and now - v.get('time', 0) >= KEEP]


def forget(record, ids):
    """El registro sin el id de lo ya quitado (el título sigue apuntado para no pedirlo otra vez enseguida)."""
    gone = set(ids)
    return {k: dict(v, id=None) if v.get('id') in gone else v for k, v in record.items()}
