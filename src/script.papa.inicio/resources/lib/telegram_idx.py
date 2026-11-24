# -*- coding: utf-8 -*-
"""Índice del grupo de Telegram: de cada vídeo, qué es (película o capítulo), su calidad y si vale (24/11/2026).

Lo usan el indexador del Mac (tools/telegram_indexar.py, carga inicial) y el servicio de la caja (lo nuevo de cada
noche). Reglas del usuario: castellano. El mínimo de 1080p NO se aplica a Telegram (decisión del 24/11/2026: «todos
los vídeos son de buena calidad»): entra todo, y entre versiones de un mismo título va primero la de más resolución.
La calidad es la resolución real si Telegram la da; si no, lo que diga el nombre; si no, '?' (el tamaño por hora
no sirve en este grupo: con ≥ 2 GB/h aún un 15 % de los capítulos es 720p). Puro.
"""
import difflib
import re
import unicodedata

_EXT = re.compile(r'\.(mkv|mp4|avi|m4v|mov|ts|webm|wmv|mpg)$', re.I)
_SIGNS = re.compile(r'@\w+|\[by [^\]]*\]|\(by [^)]*\)|\bby erpiyo\b|www\.\S+|\S+\.(?:com|net|org|eu|to)\b', re.I)
_EPISODE = (
    re.compile(r'\bS(\d{1,2})\s*E(\d{1,3})\b', re.I),                                  # S01E02
    re.compile(r'\b(\d{1,2})\s*x\s*(\d{1,3})\b', re.I),                                # 1x02, 1 x 2
    re.compile(r'\bT(?:emp(?:orada)?)?\.?\s*-?\s*(\d{1,2})\s*[/,.\-]?\s*'
               r'(?:E|C|Cap(?:[ií]tulo)?|Ep(?:isodio)?)\.?\s*-?\s*(\d{1,3})\b', re.I),     # T3 CAPITULO 3, T-8/E-96, T4 C10
    re.compile(r'\bTemporada\s*(\d{1,2})\D{1,6}?(?:Cap[ií]tulo|Episodio)\s*(\d{1,3})\b', re.I),
    re.compile(r'\bCap(?:[ií]tulo)?\.?\s*(\d{1,2})(\d{2})\b', re.I),                    # Cap.102 → 1x02
)
_LONE_EPISODE = re.compile(r'^(?:Cap(?:[ií]tulo)?|Episodio|Ep)\.?\s*(\d{1,3})\b', re.I)  # «Cap 7» (temporada aparte)
_YEAR = re.compile(r'(?:^|[(\[\s._\-·,])((?:19[2-9]|20[0-4])\d)(?=$|[)\]\s._\-·,]|(?:web|hd|bd|br|dvd|1080|720)\w*)',
                   re.I)
_JUNK = re.compile(r'[\[(]?\b(?:2160p?|1080p?|720p?|480p?|4k|uhd|hdr\d*\+?|dv|bluray|blu-ray|bdrip|brrip|web-?dl|'
                   r'webrip|hdtv|microhd|hdrip|dvdrip|x26[45]|h\.?26[45]|hevc|avc|castellano|espa[ñn]ol|spanish|'
                   r'dual|ac3|dts|aac|esp|cast|wolfmax4k|atmos|10bit|full ?hd|nf|amzn|dsnp|hmax)\b.*$', re.I)
_HD_NAME = re.compile(r'1080|2160|\b4k\b|\buhd\b|full ?hd', re.I)
_LOW_NAME = re.compile(r'\b(?:720p?|480p?|360p?|sd|hdtv|dvdrip|vhsrip|xvid)\b', re.I)
_NOT_SPANISH = re.compile(r'\b(?:catal[aà]n?|vose?|v\.o\.s\.e|subtitulad[oa]s?|subs?|latino|latam|german|'
                          r'deutsch|english|ingl[eé]s|italiano|fran[cç]ais|vo)\b', re.I)


def plain(text):
    """Para comparar: sin mayúsculas, tildes ni signos."""
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def _tidy(text):
    text = _JUNK.sub('', text)
    text = re.sub(r'[._]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return re.sub(r'^[\s\-–|:\])]+|[\s\-–|:\[(]+$', '', text).strip()


def parse(text):
    """{title, year, season, episode} de un nombre de fichero o un texto de mensaje (title None si no hay)."""
    line = next((l.strip() for l in (text or '').splitlines() if l.strip()), '')
    line = _SIGNS.sub(' ', _EXT.sub('', line)).replace('_', ' ')
    line = re.sub(r'^\s*ver\s+', '', line, flags=re.I)  # «Ver La caída de la Casa Usher»
    out = {'title': None, 'year': None, 'season': None, 'episode': None}
    for pattern in _EPISODE:
        found = pattern.search(line)
        if found:
            out['season'], out['episode'] = int(found.group(1)), int(found.group(2))
            before, after = line[:found.start()], line[found.end():]
            before_t, after_t = _tidy(before), _tidy(re.sub(r'^\s*[-–|:]\s*', '', after))
            line = before_t if len(plain(before_t)) >= 2 else ''
            if not line and after_t and _YEAR.search(' ' + after_t) is None:
                out['after'] = after_t  # «1x06 - Snowpiercer»: puede ser la serie o el título del capítulo
            break
    else:
        lone = _LONE_EPISODE.search(line)
        if lone:
            out['episode'] = int(lone.group(1))
            line = ''
    year = _YEAR.search(line)
    if year and year.start() > 0:
        out['year'] = int(year.group(1))
        line = line[:year.start()]
    title = _tidy(line)
    out['title'] = title if len(plain(title)) >= 2 else None
    return out


def describe(video):
    """Lo que dice un vídeo de sí mismo, juntando nombre de fichero y texto del mensaje."""
    by_name, by_text = parse(video.get('name')), parse(video.get('caption'))
    out = dict(by_name)
    for key in ('title', 'year', 'season', 'episode'):
        if out.get(key) is None and by_text.get(key) is not None:
            out[key] = by_text[key]
    if not out['title']:
        out['title'] = by_name.get('after') or by_text.get('after')
    out['alt'] = by_text['title'] if by_text['title'] and by_text['title'] != out['title'] else by_name.get('after')
    return out


def resolution(width, height):
    if not width or not height:
        return None
    if width >= 3200 or height >= 1800:
        return '4K'
    if width >= 1800 or height >= 1000:
        return '1080p'
    if width >= 1200 or height >= 700:
        return '720p'
    return 'SD'


def _text(video):
    return ('%s %s' % (video.get('name') or '', video.get('caption') or '')).replace('_', ' ')


def quality(video):
    """'4K', '1080p', '720p', 'SD' o '?' (no se sabe): la resolución real; si no la hay, la que diga el nombre."""
    found = resolution(video.get('width'), video.get('height'))
    if found:
        return found
    text = _text(video)
    if re.search(r'2160|\b4k\b|\buhd\b', text, re.I):
        return '4K'
    if _HD_NAME.search(text) and not _LOW_NAME.search(text):
        return '1080p'
    if re.search(r'\b720p?\b', text, re.I):
        return '720p'
    return '?'


def spanish(video):
    return not _NOT_SPANISH.search(_text(video))


def fill_series(videos):
    """Capítulos sin nombre de serie («Cap 7.mp4», «1x08 - Desde cero.mkv»): heredan la serie del mensaje vecino
    (los capítulos de una serie se suben seguidos). videos: [{id, ..., info: describe()}] → los mismos, completados."""
    ordered = sorted(videos, key=lambda v: v['id'])
    for i, v in enumerate(ordered):
        info = v['info']
        if info.get('series'):
            continue
        info['series'] = info['title']
        if info['episode'] is None:
            continue
        for j in (i - 1, i + 1, i - 2, i + 2):
            if 0 <= j < len(ordered) and abs(ordered[j]['id'] - v['id']) <= 3:
                other = ordered[j]['info']
                if other.get('title') and other['episode'] is not None and \
                        (info['season'] is None or other['season'] in (None, info['season'])):
                    if not info['title'] or plain(info.get('alt') or '') == plain(other['title']) or \
                            info['title'] != other['title'] and _looks_like_episode_title(info, other):
                        info['series'] = other['title']
                        if info['season'] is None:
                            info['season'] = other['season']
                        break
    return ordered


def _looks_like_episode_title(info, other):
    """«1x06 - Desde cero» junto a «1x05 - Snowpiercer»: el título leído es el del capítulo, no la serie."""
    return info.get('after') is not None and info['title'] == info.get('after') and other.get('title') and \
        plain(other['title']) != plain(info['title'])


def similar(a, b):
    return difflib.SequenceMatcher(None, plain(a), plain(b)).ratio()


def match_movie(title, year, results):
    """El resultado de TMDb que es esta película, o None si hay dudas. Con año: título parecido (≥ 0,8) y año ±1.
    Sin año: el título exacto; si hay varios, solo si uno es mucho más conocido (5 veces más votos)."""
    best, exact = None, []
    for r in results or []:
        names = [r.get('title') or '', r.get('original_title') or '']
        score = max(similar(title, n) for n in names)
        ryear = int((r.get('release_date') or '0000')[:4] or 0)
        if year:
            if score >= 0.8 and abs(ryear - year) <= 1 and (best is None or score > best[0]):
                best = (score, r)
        elif score == 1.0:
            exact.append(r)
    if year:
        return best[1] if best else None
    exact.sort(key=lambda r: -(r.get('vote_count') or 0))
    if len(exact) == 1 or len(exact) > 1 and (exact[0].get('vote_count') or 0) >= 5 * max(1, exact[1].get('vote_count') or 0):
        return exact[0]
    return None


_NOT_TITLES = {'corto', 'cortometraje', 'hd', 'castellano', 'espanol', 'version extendida', 'extendida',
               'remasterizada', 'documental', 'serie', 'miniserie', 'fin', 'final'}


def names(title):
    """Formas de buscar un título: tal cual, sin lo de los paréntesis y lo de los paréntesis
    («Amor Cruel (Cruel Love)» → «Amor Cruel», «Cruel Love»)."""
    out = [title]
    inside = [t for t in re.findall(r'\(([^)]{3,})\)', title or '') if plain(t) not in _NOT_TITLES]
    outside = _tidy(re.sub(r'\([^)]*\)?', ' ', title or ''))
    for name in [outside] + inside:
        if name and len(plain(name)) >= 2 and name not in out:
            out.append(name)
    return out


def match_show(title, results):
    """La serie de TMDb con nombre parecido (≥ 0,85), la más votada si hay varias. Si no, la primera de TMDb si su
    nombre contiene entero el buscado («Georgie & Mandy» → «El primer matrimonio de Georgie y Mandy»)."""
    good = [r for r in results or []
            if max(similar(title, r.get('name') or ''), similar(title, r.get('original_name') or '')) >= 0.85]
    if good:
        return max(good, key=lambda r: r.get('vote_count') or 0)
    wanted = plain(title).replace(' and ', ' y ')
    first = (results or [None])[0]
    if first and len(wanted) >= 6 and any(
            wanted in plain(first.get(k) or '').replace(' and ', ' y ') for k in ('name', 'original_name')):
        return first
    return None


ORDER = {'1080p': 0, '4K': 1, '?': 2, '720p': 3, 'SD': 4}


def rank(version):
    """Orden de preferencia entre versiones del mismo título: 1080p, 4K (pesa más por la Wi-Fi), sin dato, 720p,
    SD; dentro de cada una, la más pesada (más calidad) y la más nueva."""
    return (ORDER.get(version['quality'], 2), -(version.get('size') or 0), -version['id'])


# --- catálogo: lo mismo en el Mac (carga inicial) y en la caja (cada noche) --------------------------------------

SCHEMA = '''
CREATE TABLE IF NOT EXISTS titulos (tmdb INTEGER, tipo TEXT, titulo TEXT, año INTEGER, poster TEXT, fondo TEXT,
                                    sinopsis TEXT, nota REAL, PRIMARY KEY (tipo, tmdb));
CREATE TABLE IF NOT EXISTS pelis (tmdb INTEGER, msg INTEGER PRIMARY KEY, calidad TEXT, bytes INTEGER);
CREATE TABLE IF NOT EXISTS capitulos (tmdb INTEGER, temporada INTEGER, capitulo INTEGER, msg INTEGER PRIMARY KEY,
                                      calidad TEXT, bytes INTEGER);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT);
CREATE INDEX IF NOT EXISTS pelis_tmdb ON pelis (tmdb);
CREATE INDEX IF NOT EXISTS capitulos_tmdb ON capitulos (tmdb, temporada, capitulo);
'''


def topic(item, topics):
    """El tema (Películas/Series) de un vídeo que da el addon de Telegram parcheado (campo topic; topics: {número de
    tema: nombre}, guardado en la base); si no lo da (sin parche), se deduce: con temporada y capítulo, Series; si
    no, Películas. None: otro tema del grupo."""
    if item.get('topic') is not None:
        return topics.get(item['topic'])
    info = describe(item)
    return 'Series' if info['season'] and info['episode'] else 'Películas'


def from_addon(item, topics):
    """Un vídeo de la API del addon de Telegram (api/media) con la forma de la lista de la fase 0."""
    return {'id': item['msg_id'], 'name': item.get('name') or None, 'caption': item.get('text') or '',
            'width': item.get('w') or None, 'height': item.get('h') or None, 'size': item.get('size') or 0,
            'duration': item.get('duration') or None, 'tema': topic(item, topics)}


def find_movie(search, title, alt, year):
    """search(kind, query, year) → resultados de TMDb. El resultado que es esta película, o None."""
    for name in [n for t in (title, alt) if t for n in names(t)]:
        for y in ([year, None] if year else [None]):
            found = match_movie(name, year, search('movie', name, y))
            if found:
                return found
    return None


def find_show(search, title, alt):
    for name in [n for t in (title, alt) if t for n in names(t)]:
        found = match_show(name, search('tv', name, None))
        if found:
            return found
    return None


def catalogue(videos, search, pool_map=map):
    """Los vídeos (forma de la fase 0, con 'tema') ya en filas del catálogo:
    {'titulos': {(tipo, tmdb): resultado}, 'pelis': [...], 'capitulos': [...], 'sin_ficha': {...}, 'muestra': [...]}.
    Solo castellano (en Telegram no se exige 1080p: decisión del usuario del 24/11/2026)."""
    keep = {'Películas': [], 'Series': []}
    for v in videos:
        if v.get('tema') in keep and spanish(v):
            v['quality'], v['info'] = quality(v), describe(v)
            keep[v['tema']].append(v)
    series = [v for v in fill_series(keep['Series']) if v['info']['season'] and v['info']['episode']]
    movies = [v for v in keep['Películas'] if v['info']['title']]
    keys_m = list({(v['info']['title'], v['info'].get('alt'), v['info']['year']) for v in movies})
    keys_s = list({_show_key(v['info']) for v in series if v['info']['series']})
    found_m = dict(zip(keys_m, pool_map(lambda k: find_movie(search, *k), keys_m)))
    found_s = dict(zip(keys_s, pool_map(lambda k: find_show(search, *k), keys_s)))
    out = {'titulos': {}, 'pelis': [], 'capitulos': [], 'sin_ficha': {}, 'muestra': []}
    for v in movies:
        i = v['info']
        r = found_m[(i['title'], i.get('alt'), i['year'])]
        if not r:
            out['sin_ficha']['%s (%s)' % (i['title'], i['year'] or '?')] = v['name'] or v['caption'][:60]
            continue
        out['titulos'][('peliculas', r['id'])] = r
        out['pelis'].append((r['id'], v['id'], v['quality'], v['size']))
        out['muestra'].append(('película', v['name'] or v['caption'][:60],
                               '%s (%s)' % (r.get('title'), (r.get('release_date') or '')[:4])))
    for v in series:
        i = v['info']
        r = found_s.get(_show_key(i)) if i['series'] else None
        if not r:
            out['sin_ficha'][i['series'] or '(sin nombre)'] = v['name'] or v['caption'][:60]
            continue
        out['titulos'][('series', r['id'])] = r
        out['capitulos'].append((r['id'], i['season'], i['episode'], v['id'], v['quality'], v['size']))
        out['muestra'].append(('capítulo', v['name'] or v['caption'][:60],
                               '%s %dx%02d' % (r.get('name'), i['season'], i['episode'])))
    return out


def _show_key(info):
    return info['series'], info.get('alt') if info['series'] == info['title'] else None


def title_row(tipo, r):
    date = r.get('release_date' if tipo == 'peliculas' else 'first_air_date') or ''
    return (r['id'], tipo, r.get('title') or r.get('name'), int(date[:4]) if date[:4].isdigit() else None,
            r.get('poster_path'), r.get('backdrop_path'), r.get('overview'), r.get('vote_average'))


def store(db, found, last_msg, peer, topics=None):
    """Guarda en la base (sqlite3 abierta) lo que devolvió catalogue(); lo ya guardado no se duplica. El grupo y sus
    temas solo se guardan aquí (y en el Mac): el código es público."""
    db.executescript(SCHEMA)
    db.executemany('INSERT OR REPLACE INTO titulos VALUES (?,?,?,?,?,?,?,?)',
                   [title_row(tipo, r) for (tipo, _), r in found['titulos'].items()])
    db.executemany('INSERT OR IGNORE INTO pelis VALUES (?,?,?,?)', found['pelis'])
    db.executemany('INSERT OR IGNORE INTO capitulos VALUES (?,?,?,?,?,?)', found['capitulos'])
    db.executemany('INSERT OR REPLACE INTO estado VALUES (?,?)', [('grupo', str(peer)), ('ultimo_msg', str(last_msg))]
                   + [('tema:%s' % n, name) for n, name in (topics or {}).items()])
    db.commit()


def topics(db):
    """{número de tema: 'Películas'/'Series'} guardado en la base."""
    try:
        rows = db.execute("SELECT clave, valor FROM estado WHERE clave LIKE 'tema:%'").fetchall()
    except Exception:
        return {}
    return {int(k[5:]): v for k, v in rows if k[5:].isdigit()}


def last_msg(db):
    try:
        row = db.execute("SELECT valor FROM estado WHERE clave = 'ultimo_msg'").fetchone()
    except Exception:
        return 0
    return int(row[0]) if row and str(row[0]).isdigit() else 0
