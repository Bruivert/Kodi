# -*- coding: utf-8 -*-
"""El catálogo de Palantir para la búsqueda de la skin (la lupa).

Pedirle la búsqueda a Palantir tarda: arranca en ~4,5 s cada vez (su código está ofuscado) y su consulta compara
título a título en Python. Aquí se lee su base directamente (SQLite, solo lectura) y se montan las mismas fichas que
pone en su lista: al elegir una, Palantir hace lo de siempre (enlaces y reproducción, o temporadas).
Puro: las rutas llegan de fuera.
"""
import base64
import unicodedata
from urllib import parse

PALANTIR = 'plugin://plugin.video.palantir3/?'
IMAGES = 'https://image.tmdb.org/t/p/'
YOUTUBE = 'plugin://plugin.video.youtube/play/?video_id=%s'


def _fold(ch):
    """Una letra como la deja map_string de Palantir: base sin acento y en mayúscula; nada si es signo."""
    if ch == ' ':
        return ' '
    if ord(ch) > 0xFF:
        return ''
    base = unicodedata.normalize('NFKD', ch)[0]
    return base.upper() if base.isascii() and base.isalnum() else ''


def normalize(text):
    """'Señor O'Brien' → 'SENOR OBRIEN', como compara Palantir en su búsqueda (iREGEXP con map_string)."""
    return ''.join(_fold(ch) for ch in (text or '').strip()).strip()


def p3_encode(text):
    """El p3b64encode de Palantir: base64 con las dos partes del texto al revés."""
    value = base64.b64encode(text.encode('utf-8'))
    cut = int(len(value) / 4)
    value = value.replace(b'=', b'')
    return parse.quote(value[:cut][::-1] + value[cut:][::-1])


def p3_decode(value):
    value = parse.unquote(value).encode('utf-8').replace(b'?', b'')
    pad = (4 - len(value) % 4) % 4
    cut = int((len(value) + pad) / 4)
    return base64.b64decode(value[:cut][::-1] + value[cut:][::-1] + b'=' * pad).decode('utf-8')


def p3_url(fields):
    """La dirección de una ficha de Palantir (su P3Item.tourl: el dict con las claves ordenadas)."""
    text = '{%s}' % ', '.join('"%s": %r' % (key, fields[key]) for key in sorted(fields))
    return PALANTIR + p3_encode(text)


def _image(size, path):
    if not path:
        return ''
    if path.lower().startswith('http'):
        return path
    return IMAGES + size + (path if path.startswith('/') else '/' + path)


def _rating(value):
    try:
        return float(str(value or '').split('/')[0])
    except ValueError:
        return None


def to_item(kind, row):
    """Elemento de la fila (forma de filas.to_item) para una película o serie de la base de Palantir."""
    movie = kind == 'peliculas'
    title = (row.get('titulo') or '').replace('\\n', '').strip()
    fecha = row.get('fecha') or ''
    poster, fanart, logo = _image('w500', row.get('poster')), _image('w1280', row.get('fondo')), \
        _image('w500', row.get('clearlogo'))
    art = {'poster': poster, 'thumb': poster, 'fanart': fanart, 'clearlogo': logo}

    info = {'title': title, 'mediatype': 'movie' if movie else 'tvshow', 'plot': row.get('plot'),
            'mpaa': row.get('mpaa'), 'rating': _rating(row.get('rating'))}
    if fecha[:4].isdigit():
        info['year'], info['premiered'] = int(fecha[:4]), fecha
    if movie:
        info['duration'] = row.get('duration')
    genres = [g for g in (row.get('genero') or '').split('#') if g]
    if genres:
        info['genre'] = genres
    if row.get('trailer'):
        info['trailer'] = YOUTUBE % row['trailer']

    fields = {'label': title, 'tmdb': str(row['tmdb']), 'fecha': row.get('fecha'), 'plot': row.get('plot'),
              'poster': row.get('poster'), 'fanart': row.get('fondo'), 'clearlogo': row.get('clearlogo'),
              'mpaa': row.get('mpaa') or '',  # Palantir mira si lleva "+18"
              'rating': row.get('rating')}
    if movie:
        fields.update(title=title, duration=row.get('duration'), action='selectvideos_', content='movies',
                      isPlayable=True)
    else:
        fields.update(tvshowtitle=title, action='listado_temporadaS', content='tvshows', page=0)

    return {'label': title, 'path': p3_url({k: v for k, v in fields.items() if v is not None}), 'folder': not movie,
            'art': {k: v for k, v in art.items() if v}, 'info': {k: v for k, v in info.items() if v not in (None, '')},
            'uniqueids': {'tmdb': str(row['tmdb'])}, 'properties': {'IsPlayable': 'true'} if movie else {}}
