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
_SIGNS = re.compile(r'@\w+|\[by [^\]]*\]|\(by [^)]*\)|by ?erpiyo\b|by ?runneo\b|www\.\S+|\S+\.(?:com|net|org|eu|to|mx)\b|'
                    r'^\s*\[[^\]]*\]', re.I)
_SYMBOLS = re.compile(r'[^\w\s\-.,:;!?¿¡\'"()\[\]&/·+ª]')  # emojis y adornos («😒De Perdidos a Río ⟬2023⟭»)
_EPISODE = (
    re.compile(r'(?<!\d)S(\d{1,2})\s*E(\d{1,3})\b', re.I),                             # S01E02, HystrS01E05
    re.compile(r'\bS(\d{2})(\d{2})\b', re.I),                                          # S0104
    re.compile(r'(?<!\d)(\d{1,2})\s*x\s*(\d{1,3})(?!\d)', re.I),                       # 1x02, 1 x 2, Taboo720p1x01
    re.compile(r'\bT(?:emp(?:orada)?)?\.?\s*-?\s*(\d{1,2})\s*[/,.\-]?\s*'
               r'(?:E|C|Cap(?:[ií]tulo)?|Ep(?:isodio)?)\.?\s*-?\s*(\d{1,3})\b', re.I),     # T3 CAPITULO 3, T-8/E-96, T4 C10
    re.compile(r'\bTemporada\s*(\d{1,2})\D{1,6}?(?:Cap[ií]tulo|Episodio)\s*(\d{1,3})\b', re.I),
    re.compile(r'Cap(?![ií]t)\.?\s*(\d{1,2})(\d{2})(?!\d)', re.I),                    # Cap.102, 720pCap_309 → 3x09
)
# «Cap 7», «Capitulo 135» (telenovelas), «Ep_6 … online - Movistar», «El Hombre Equivocado Cap 14»: sin temporada
_LONE_EPISODE = re.compile(r'(?:^|\s)(?:Cap[ií]tulo|Cap|Episodio|Ep)\.?\s*(\d{1,3})\b', re.I)
_YEAR = re.compile(r'(?:^|[(\[\s._\-·,])((?:19[2-9]|20[0-4])\d)(?=$|[)\]\s._\-·,/]|(?:web|hd|bd|br|dvd|1080|720)\w*)',
                   re.I)
_JUNK = re.compile(r'[\[(]?\b(?:2160p?|1080p?|720p?|480p?|4k|uhd|hdr\d*\+?|dv|bluray|blu-ray|bdrip|brrip|web-?dl|'
                   r'webrip|hdtv|microhd|hdrip|dvdrip|p?x26[45]|h\.?26[45]|hevc|avc|castellano|espa[ñn]ol|spanish|'
                   r'dual|ac3|dts|aac|esp|cast|wolfmax4k|atmos|10bit|full ?hd|nf|amzn|dsnp|hmax|online|movistar)\b.*$', re.I)
_HD_NAME = re.compile(r'1080|2160|\b4k\b|\buhd\b|full ?hd', re.I)
_LOW_NAME = re.compile(r'\b(?:720p?|480p?|360p?|sd|hdtv|dvdrip|vhsrip|xvid)\b', re.I)
_NOT_SPANISH = re.compile(r'\b(?:catal[aà]n?|vose?|v\.o\.s\.e|latino|latam|german|deutsch|italiano|fran[cç]ais|vo)\b',
                          re.I)
_MAYBE_NOT_SPANISH = re.compile(r'\b(?:subtitulad[oa]s?|subs?|english|ingl[eé]s)\b', re.I)  # salvo si dice castellano
_SPANISH = re.compile(r'castellano|espa[ñn]ol|\bspanish\b|\besp\b|🇪🇸', re.I)
# En la carátula, «Idioma original: italiano» no dice nada del audio: solo cuentan estas
_HEAD_NOT_SPANISH = re.compile(r'\b(?:latino|latam|vose?|v\.o\.s\.e|subtitulad[oa]|catal[aà]n?)\b', re.I)


def plain(text):
    """Para comparar: sin mayúsculas, tildes ni signos."""
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower().replace('&', ' y ')
    return ' '.join('y' if w == 'and' else w for w in re.sub(r'[^a-z0-9]+', ' ', text).split())


def _tidy(text):
    text = _JUNK.sub('', text)
    text = re.sub(r'[\s\-]*\bTemp(?:orada)?\.?\s*\d+\b.*$', '', text, flags=re.I)
    text = re.sub(r'\s*\([^)]*$', '', text)
    text = re.sub(r'[._]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return re.sub(r'^[\s\-–|:\])]+|[\s\-–|:\[(]+$', '', text).strip()


def parse(text, lone=True):
    """{title, year, season, episode} de un nombre de fichero o un texto de mensaje (title None si no hay)."""
    lines = [l.strip() for l in unicodedata.normalize('NFKC', text or '').splitlines() if l.strip()]
    line = lines[0] if lines else ''
    line = re.sub(r'[⟬〔【]', '(', re.sub(r'[⟭〕】]', ')', line))
    line = _SYMBOLS.sub(' ', _SIGNS.sub(' ', _EXT.sub('', line))).replace('_', ' ')
    if ' ' not in line.strip() and line.count('-') >= 2:  # «esta-abuela-es-un-peligro-3-2011-720p»
        line = line.replace('-', ' ')
    line = re.sub(r'^\s*(?:ver|t[ií]tulo\s*:)\s+', '', line, flags=re.I)  # «Ver La caída…», «Título: …»
    out = {'title': None, 'year': None, 'season': None, 'episode': None}
    lead = re.match(r'^\s*\(?((?:19[2-9]|20[0-4])\d)\)?\s*[-–.]?\s+(?=\D)', line)  # «2015 - Mad Max…», «(1992) Una monja…»
    if lead and re.match(r'^\s*\(|^\s*\d{4}\s*[-–.]', line):
        out['year'], line = int(lead.group(1)), line[lead.end():]
    for pattern in _EPISODE:
        found = pattern.search(line)
        if found:
            out['season'], out['episode'] = int(found.group(1)), int(found.group(2))
            before, after = line[:found.start()], line[found.end():]
            before_t, after_t = _tidy(before), _tidy(re.sub(r'^\s*[-–|:]\s*', '', after))
            line = before_t if len(plain(before_t)) >= 2 else ''
            if not line and after_t:
                year = _YEAR.search(' ' + after_t)
                if year:  # «1x04 - Maniac (2018)»: la serie, con su año
                    after_t, out['year'] = _tidy(after_t[:max(0, year.start() - 1)]), int(year.group(1))
                if len(plain(after_t)) >= 2:
                    out['after'] = after_t  # «1x06 - Snowpiercer»: puede ser la serie o el título del capítulo
            break
    else:
        found = _LONE_EPISODE.search(line) if lone else None  # en películas, «Strangers: Capítulo 1» es el título
        if found:
            out['episode'] = int(found.group(1))
            line = line[:found.start()]
        else:  # el capítulo en otra línea del mensaje («Sweet Home» / «T3C8»)
            for other in lines[1:4]:
                found = next((m for m in (p.search(other) for p in _EPISODE) if m), None)
                if found:
                    out['season'], out['episode'] = int(found.group(1)), int(found.group(2))
                    break
    year = _YEAR.search(line)
    if year and year.start() > 0:
        out['year'] = int(year.group(1))
        line = line[:year.start()]
    if out['year'] is None:  # «SMILE (SONRIE)» / «2022» en la línea siguiente
        alone = next((m for m in (re.fullmatch(r'\(?((?:19[2-9]|20[0-4])\d)\)?', l.strip()) for l in lines[1:3]) if m), None)
        if alone:
            out['year'] = int(alone.group(1))
    title = _tidy(line)
    out['title'] = title if len(plain(title)) >= 2 else None
    return out


def describe(video, lone=True):
    """Lo que dice un vídeo de sí mismo, juntando nombre de fichero y texto del mensaje."""
    by_name, by_text = parse(video.get('name'), lone), parse(video.get('caption'), lone)
    out = dict(by_name)
    if by_text['season'] and by_text['episode'] and (by_name['season'], by_name['episode']) != \
            (by_text['season'], by_text['episode']):
        out['season'], out['episode'] = by_text['season'], by_text['episode']  # «13_T1_C1.mp4» | «2x13»
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


def probe_resolution(head):
    """(ancho, alto) leídos de los primeros bytes de un vídeo, o None. MKV: los campos PixelWidth (B0) y PixelHeight
    (BA) de la pista de vídeo; AVI: la cabecera «avih»; MP4: la caja «tkhd» (si el índice va al principio)."""
    import struct
    data = bytes(head or b'')
    if data[:4] == b'\x1a\x45\xdf\xa3':  # MKV / WebM
        start = data.find(b'\xe0')  # Video
        while start != -1:
            w = _ebml_uint(data, start, 0xB0)
            h = _ebml_uint(data, start, 0xBA)
            if w and h:
                return w, h
            start = data.find(b'\xe0', start + 1)
        return None
    if data[:4] == b'RIFF' and data[8:12] == b'AVI ':
        at = data.find(b'avih')
        if at != -1 and len(data) >= at + 48:
            w, h = struct.unpack('<II', data[at + 40:at + 48])
            return (w, h) if 0 < w < 10000 and 0 < h < 10000 else None
        return None
    at = data.find(b'tkhd')
    while at != -1 and len(data) >= at + 84:
        w, h = struct.unpack('>II', data[at + 76:at + 84])
        if w >> 16 and h >> 16:
            return w >> 16, h >> 16
        at = data.find(b'tkhd', at + 4)
    return None


def _ebml_uint(data, start, element, window=200):
    """El valor del elemento EBML de un byte de id (element) en los window bytes siguientes a start."""
    i = start + 1
    end = min(len(data), start + window)
    while i < end - 2:
        if data[i] == element and data[i + 1] & 0x80:  # tamaño de un byte (0x81 = 1 byte, 0x82 = 2…)
            size = data[i + 1] & 0x7F
            if 1 <= size <= 4 and i + 2 + size <= len(data):
                return int.from_bytes(data[i + 2:i + 2 + size], 'big')
        i += 1
    return None


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


def spanish(video, head=''):
    """¿En castellano? Fuera catalán, VOSE, latino…; «Subs»/«Inglés» solo si no dice también castellano («Castellano
    Subs» vale). La carátula (head) cuenta para lo primero: «Huesos … Latino» deja fuera sus capítulos."""
    text = _text(video)
    if _NOT_SPANISH.search(text) or _HEAD_NOT_SPANISH.search(head or ''):
        return False
    return not _MAYBE_NOT_SPANISH.search(text) or bool(_SPANISH.search(text))


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


_ROMAN = {'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}


def numbers(text):
    """Los números de un título (secuelas: «2», «II», «2ª»), sin los años: «Viernes 13 parte 2» → {13, 2}."""
    out = set()
    for word in plain(text).split():
        digits = re.fullmatch(r'(\d+)(?:a|o|st|nd|rd|th)?', word)
        if digits and not re.fullmatch(r'(?:19|20)\d\d', digits.group(1)):
            out.add(int(digits.group(1)))
        elif word in _ROMAN:
            out.add(_ROMAN[word])
    return out


def _same_numbers(a, b):
    """Los números de secuela no se contradicen: solo cuenta si los dos títulos llevan («Piratas del Caribe 2» →
    «Piratas del Caribe: El cofre…» vale; «parte 2» → «parte III», no)."""
    x, y = numbers(a), numbers(b)
    return not x or not y or x == y


def similar(a, b):
    return difflib.SequenceMatcher(None, plain(a), plain(b)).ratio()


def match_movie(title, year, results, loose=False):
    """El resultado de TMDb que es esta película, o None si hay dudas. Con año: título parecido (≥ 0,8) y año ±1.
    Sin año: el título exacto; si hay varios, solo si uno es mucho más conocido (5 veces más votos).
    Los números de secuela tienen que coincidir.
    loose (solo con año): también vale que un título contenga entero al otro («Alli me encontraras Finding You» →
    «Allí me encontrarás»), si el más corto tiene al menos 2 palabras o 8 letras."""
    best, exact = None, []
    for r in results or []:
        names = [r.get('title') or '', r.get('original_title') or '']
        if not any(_same_numbers(title, n) for n in names if n):
            continue  # «Viernes 13 parte 2» no es «Viernes 13, parte III»
        score = max(similar(title, n) for n in names)
        bare = lambda t: ' '.join(w for w in plain(t).split() if not w.isdigit() and w not in _ROMAN)  # noqa: E731
        whole = loose and any(_starts(n, title) for n in names if n)  # «Ong Bak» → «Ong Bak: El guerrero Muay Thai»
        if len(plain(title)) < 8 and not whole and max(similar(bare(title), bare(n)) for n in names) < 0.9:
            continue  # títulos cortos: «Amal» no es «Amalur» («Sissi 1» sí es «Sissi»)
        ryear = int((r.get('release_date') or '0000')[:4] or 0)
        if year:
            if loose and score < 0.8 and any(_contains(title, n, 6) or _starts(n, title) for n in names if n):
                score = 0.79
            rank = (numbers(title) == max((numbers(n) for n in names), key=len), ryear == year, score)  # «75 días»
            # antes que «Días»; el del año exacto antes que uno muy parecido de un año más o menos
            if score >= (0.79 if loose else 0.8) and abs(ryear - year) <= 1 and (best is None or rank > best[0]):
                best = (rank, r)
        elif score == 1.0 and not loose and r.get('release_date'):
            exact.append(r)
    if year:
        return best[1] if best else None
    exact.sort(key=lambda r: -(r.get('vote_count') or 0))
    if len(exact) == 1 or len(exact) > 1 and (exact[0].get('vote_count') or 0) >= 5 * max(1, exact[1].get('vote_count') or 0):
        return exact[0]
    return None


_NOT_TITLES = {'corto', 'cortometraje', 'hd', 'castellano', 'espanol', 'version extendida', 'extendida',
               'remasterizada', 'documental', 'serie', 'miniserie', 'fin', 'final', 'la pelicula', 'pelicula',
               'the movie', 'el musical'}


def names(title, partial=True):
    """Formas de buscar un título: tal cual, sin lo de los paréntesis y lo de los paréntesis («Amor Cruel (Cruel Love)»
    → «Amor Cruel», «Cruel Love»), sin numeración delante («01 - Harry Potter…», «z Ocho apellidos…») y cada parte
    separada por « - ». Cada forma se comprueba luego contra TMDb, así que probar de más no mete errores."""
    out = [title]
    inside = [t for t in re.findall(r'\(([^)]{3,})\)', title or '') if plain(t) not in _NOT_TITLES]
    outside = _tidy(re.sub(r'\([^)]*\)?', ' ', title or ''))
    unnumbered = re.sub(r'^(?:\d{1,2}\s*-?\s+|z\s+)(?=[^\W\d])', '', outside or '', flags=re.I)
    pieces = re.split(r'\s+-\s+', unnumbered)
    parts = [p.strip() for p in pieces if len(plain(p)) >= 3 and not plain(p).isdigit() and plain(p) not in _NOT_TITLES]
    more = inside + [unnumbered] + (parts if len(pieces) > 1 else []) if partial else [unnumbered]
    for name in [outside] + more:
        if name and len(plain(name)) >= 2 and name not in out:
            out.append(name)
    return out


def _starts(longer, shorter):
    """¿El título de TMDb (longer) empieza por el buscado? («Padre no hay más que uno 4» → «… 4: Campanas de boda»)."""
    a, b = plain(longer), plain(shorter)
    return len(b) >= 6 and (' ' in b or len(b) >= 8) and a != b and a.startswith(b + ' ')


def _contains(longer, shorter, minimum):
    """¿shorter está entero (palabras completas) dentro de longer? shorter: al menos 2 palabras o 8 letras."""
    a, b = plain(longer), plain(shorter)
    return len(b) >= minimum and (' ' in b or len(b) >= 8) and a != b and (' %s ' % b) in (' %s ' % a)


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
    if first and any(_contains(title, first.get(k) or '', 8) for k in ('name', 'original_name')):
        return first  # «Mentes Criminales Evolution» → «Mentes criminales», «El detective Endeavour» → «Endeavour»
    return None


ORDER = {'1080p': 0, '4K': 1, '?': 2, '720p': 3, 'SD': 4}


def rank(version):
    """Orden de preferencia entre versiones del mismo título: 1080p, 4K (pesa más por la Wi-Fi), sin dato, 720p,
    SD; dentro de cada una, la más pesada (más calidad) y la más nueva."""
    return (ORDER.get(version['quality'], 2), -(version.get('size') or 0), -version['id'])


# --- carátulas y partes ------------------------------------------------------------------------------------------
# En el grupo cada título suele empezar con una foto (la carátula) con el nombre, el año, la sinopsis y a veces la
# temporada; debajo van sus vídeos, que a veces solo dicen «3», «Cap 39» o «Ep_6 … online - Movistar». La carátula
# completa lo que el vídeo no dice (25/11/2026, a raíz de lo que contó el usuario).

_HEAD_SEASON = re.compile(r'temporada\s*:?\s*0?(\d{1,2})\b|#temporada0?(\d{1,2})\b', re.I)
_HEAD_COUNT = re.compile(r'(\d{1,2})\s+temporadas?\b|temporadas\s*:\s*(\d{1,2})', re.I)
_HEAD_SINGLE = re.compile(r'mini\s*-?\s*serie|temporada\s*:?\s*[uú]nica', re.I)
_ONLY_SEASON = re.compile(r'^\W*(?:#?temporada\s*:?\s*0?\d{1,2}|t\s*\d{1,2})\W*$', re.I)
_NOT_NAME = re.compile(r'sinopsis|sipnosis|idioma|g[eé]nero|director|reparto|a[ñn]o\s*:|duraci[oó]n|pa[ií]s|nota|serie de tv|'
                       r'cap[ií]tulos?\s*:|episodios?\b|temporadas?\s*:|audio|subt[ií]', re.I)


def head_info(text):
    """De la carátula: {title, alt, year, season, single}. title None si solo dice la temporada («TEMPORADA 3»).
    season: la que diga («Temporada: 2», «#Temporada01»); single: la serie tiene una sola temporada
    («1 temporada», «Miniserie»)."""
    lines = [l.strip(' -–•') for l in unicodedata.normalize('NFKC', text or '').splitlines()]
    lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    names = [l for l in lines[:3] if not _ONLY_SEASON.match(l) and not _NOT_NAME.search(l)]
    first = parse(names[0]) if names else {'title': None, 'year': None}
    second = parse(names[1]) if len(names) > 1 and len(names[1]) <= 60 else {'title': None}
    found = _HEAD_SEASON.search(text or '')
    count = _HEAD_COUNT.search(text or '')
    count = int(next(g for g in count.groups() if g)) if count else None
    return {'title': first['title'], 'alt': second['title'] if second['title'] != first['title'] else None,
            'year': first.get('year'), 'season': int(next(g for g in found.groups() if g)) if found else None,
            'single': bool(_HEAD_SINGLE.search(text or '')) or count == 1}


def with_headers(rows):
    """Los vídeos de los mensajes del grupo (fotos, vídeos y textos de mensajes.json o de la API del addon), cada uno
    con 'head' (lo que dice su carátula: head_info + 'text') y 'bloque' (los vídeos de una misma carátula). Una foto
    o un texto vacío cierran el bloque anterior."""
    named, season, block, videos = {}, {}, {}, []
    for r in sorted(rows, key=lambda r: r['id']):
        t = r.get('tema')
        if r.get('tipo') in ('foto', 'texto'):
            block[t] = r['id']
            text = (r.get('caption') or '').strip()
            info = head_info(text) if text else {'title': None, 'season': None}
            if info['title'] or not text:
                named[t], season[t] = (dict(info, text=text) if text else None), (info.get('season'), False)
            elif info['season']:
                season[t] = (info['season'], True)  # «TEMPORADA 3» suelta, justo antes de sus capítulos
        elif r.get('tipo', 'video') == 'video':
            head = dict(named.get(t) or {})
            if (season.get(t) or (None,))[0]:
                head['season'], head['season_alone'] = season[t]
            videos.append(dict(r, head=head, bloque=block.get(t, 0)))
    return videos


def _junk(title):
    """Un título que no dice nada: vacío o un número corto («16», «3»); «1923» o «1670» sí son títulos."""
    p = plain(title)
    return not p or len(p) < 2 or (p.isdigit() and len(p) <= 3)


def _same(a, b):
    """¿Hablan del mismo título? Parecidos o uno dentro del otro («Twisted Metal» / «Twisted Metal [Temporada 1]»)."""
    x, y = plain(a), plain(b)
    return bool(x and y) and (similar(x, y) >= 0.75 or _contains(x, y, 4) or _contains(y, x, 4))


def describe_full(video):
    """describe() completado con la carátula del vídeo. La carátula solo cuenta si el vídeo no dice de qué es, o si
    dice lo mismo que ella: en el tema Series a veces se suben capítulos sin foto, y la última carátula es de otra
    serie. info['head_ok']: si se ha usado."""
    movie = video.get('tema') != 'Series'
    info = describe(video, lone=not movie)
    head = video.get('head') or {}
    own = info['title'] if not (_junk(info['title']) and not (movie and info['title'])) else None
    if own and head.get('title') and not any(_same(own, h) for h in (head['title'], head.get('alt')) if h):
        # la carátula es de otra cosa; una «TEMPORADA 3» suelta justo antes de los capítulos sí vale
        head = {'season': head['season']} if head.get('season_alone') and video.get('tema') == 'Series' else {}
    elif own and not head.get('title'):
        head = {k: head[k] for k in ('season',) if head.get(k)} if video.get('tema') == 'Series' else {}
    info['head_ok'] = bool(head)
    if video.get('tema') == 'Series':
        if _junk(info['title']) and head.get('title'):
            info['title'], info['alt'] = head['title'], head.get('alt') or info.get('alt')
        if info['episode'] is None:
            alone = re.fullmatch(r'\s*(\d{1,3})\s*(?:\n.*)?', video.get('caption') or '', re.S) or \
                re.fullmatch(r'(\d{1,3})(?:\.\w+)?', (video.get('name') or '').strip())
            if alone:
                info['episode'] = int(alone.group(1))
        if info['season'] is None:
            if head.get('season'):
                info['season'] = head['season']
            elif head.get('single') and info['episode']:
                info['season'] = 1
        if info['episode'] is None and info['season']:  # «Rita 307» con la carátula «TEMPORADA 3»
            code = re.search(r'(?<!\d)%d(\d{2})(?!\d)' % info['season'], video.get('name') or '')
            if code:
                info['episode'] = int(code.group(1))
                own = re.sub(r'\s*\d{3}.*$', '', info['title'] or '')
                info['title'] = own if not _junk(own) else head.get('title')
    else:
        if not own and head.get('title'):
            info['title'], info['year'] = head['title'], info['year'] or head.get('year')
            info['alt'] = head.get('alt') or info.get('alt')
        elif head.get('title'):
            info['year'] = info['year'] or head.get('year')
            if not info.get('alt') and plain(head['title']) != plain(info['title']):
                info['alt'] = head['title']
    return info


_PART = (re.compile(r'^(?P<n>[1-9])_[2-9]_(?P<base>.+)$'),                      # «1_2_En el oeste…»
         re.compile(r'^(?P<base>.+?)\s*\((?P<n>[1-9])\)$'),                     # «Ong Bak (2)»
         re.compile(r'^(?P<base>.+?)\s+(?:parte?|part|pt|cd)\.?\s*(?P<n>[1-9])$', re.I),  # «… Parte 2», «CD1»
         re.compile(r'^(?P<base>.+\(\d{4}\))\s+(?P<n>[1-9])$'))                 # «La monja 2 (2023) 1»
PART_MAX = 80 * 60  # una parte dura menos que una película: «Sinsajo Parte 1» (122 min) es una película entera


def part_of(video):
    """(nombre común, número de parte) si el fichero es una parte de una película, o None."""
    name = _SIGNS.sub(' ', _EXT.sub('', (video.get('name') or '').strip())).replace('_', ' ').strip()
    name = re.sub(r'^([1-9]) ([2-9]) ', r'\1_\2_', name)
    name = _JUNK.sub('', name).strip(' -.')
    for pattern in _PART:
        found = pattern.match(name)
        if found:
            return plain(found.group('base')), int(found.group('n'))
    return None


def movie_parts(videos):
    """{msg de la parte 1: [msgs de todas las partes en orden]} de las películas partidas: vídeos del mismo bloque
    con el mismo nombre y partes 1, 2… (cada una de menos de PART_MAX, si se sabe lo que dura)."""
    groups = {}
    for v in videos:
        found = part_of(v)
        if found:
            groups.setdefault((v.get('bloque'), found[0]), []).append((found[1], v))
    out = {}
    for parts in groups.values():
        parts.sort(key=lambda p: (p[0], p[1]['id']))
        numbers = [n for n, _ in parts]
        if len(parts) >= 2 and numbers == list(range(1, len(parts) + 1)) and \
                all(not v.get('duration') or v['duration'] < PART_MAX for _, v in parts):
            out[parts[0][1]['id']] = [v['id'] for _, v in parts]
    return out


# --- catálogo: lo mismo en el Mac (carga inicial) y en la caja (cada noche) --------------------------------------

SCHEMA = '''
CREATE TABLE IF NOT EXISTS titulos (tmdb INTEGER, tipo TEXT, titulo TEXT, año INTEGER, poster TEXT, fondo TEXT,
                                    sinopsis TEXT, nota REAL, PRIMARY KEY (tipo, tmdb));
CREATE TABLE IF NOT EXISTS pelis (tmdb INTEGER, msg INTEGER PRIMARY KEY, calidad TEXT, bytes INTEGER);
CREATE TABLE IF NOT EXISTS capitulos (tmdb INTEGER, temporada INTEGER, capitulo INTEGER, msg INTEGER PRIMARY KEY,
                                      calidad TEXT, bytes INTEGER);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS partes (msg INTEGER PRIMARY KEY, primera INTEGER, numero INTEGER);
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
    """Un mensaje de la API del addon de Telegram (api/media, vídeos y fotos) con la forma de mensajes.json."""
    return {'id': item['msg_id'], 'tipo': 'foto' if item.get('kind') == 'photo' else 'video',
            'name': item.get('name') or None, 'caption': item.get('text') or '',
            'width': item.get('w') or None, 'height': item.get('h') or None, 'size': item.get('size') or 0,
            'duration': item.get('duration') or None, 'tema': topic(item, topics)}


def find_movie(search, title, alt, year):
    """search(kind, query, year) → resultados de TMDb. El resultado que es esta película, o None. Se prueban todas las
    formas del nombre y, de lo encontrado, gana lo que más se parece al título completo («Torrente III - El
    Protector»: la parte «El Protector» encuentra «El Protector» (2004) y «Torrente 3: El protector»; gana esta).
    Solo si no hay ninguna coincidencia clara, «un título contiene al otro» (con el título tal cual y el año)."""
    found, full = [], [t for t in (title, alt) if t]
    for name in [n for t in full for n in names(t, partial=bool(year))]:  # sin año, ni trozos ni paréntesis
        for y in ([year, None] if year else [None]):
            results = search('movie', name, y)
            for r in [match_movie(n, year, results) for n in [name] + full]:  # lo hallado se mide también
                if r and r['id'] not in [f['id'] for f in found]:            # contra el título completo
                    found.append(r)
    sequel = any(numbers(t) for t in full)
    if year and sequel and not any(numbers(t) and numbers(t) == numbers(r.get(k) or '') for r in found for t in full
                                   for k in ('title', 'original_title')):
        for name in full:  # «Padre no hay más que uno 2» → «…2: la llegada de la suegra», no la primera
            for y in (year, None):
                r = match_movie(name, year, search('movie', name, y), loose=True)
                if r and r['id'] not in [f['id'] for f in found]:
                    found.append(r)
    if found:
        return max(found, key=lambda r: (any(numbers(t) and numbers(t) == numbers(r.get(k) or '') for t in full
                                             for k in ('title', 'original_title')),
                                         bool(year) and (r.get('release_date') or '')[:4] == str(year),
                                         max(similar(t, r.get(k) or '') for t in full
                                             for k in ('title', 'original_title'))))
    if year:
        for name in [t for t in (title, alt) if t]:
            for y in (year, None):
                r = match_movie(name, year, search('movie', name, y), loose=True)
                if r:
                    return r
    return None


# Series que el grupo sube con el nombre abreviado a propósito (24/11/2026): nombre leído (plain) → búsqueda en TMDb
ALIASES = {'csi lv': 'CSI: Crime Scene Investigation', 'l3yord3nuve': 'Law & Order: Special Victims Unit',
           'lyouve': 'Law & Order: Special Victims Unit', 'ley y orden uve': 'Law & Order: Special Victims Unit',
           'ccavm': 'How I Met Your Mother', 'aoshield': "Marvel's Agents of S.H.I.E.L.D.",
           'tmithcastle': 'The Man in the High Castle', 'tdetective': 'True Detective', 'sobrenatural': 'Supernatural',
           'sw andor': 'Andor', 'star wars andor': 'Andor', 'halo la serie': 'Halo',
           'instituto mckinley': 'Freaks and Geeks', 'las brujas de e e': 'Witches of East End',
           'twin peaks el regreso': 'Twin Peaks'}


def find_show(search, title, alt):
    for name in [ALIASES[plain(t)] for t in (title, alt) if t and plain(t) in ALIASES] + \
            [n for t in (title, alt) if t for n in names(t)]:
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
        if v.get('tema') not in keep:
            continue
        info = describe_full(v)
        if spanish(v, (v.get('head') or {}).get('text') if info['head_ok'] else ''):
            v['quality'], v['info'] = quality(v), info
            keep[v['tema']].append(v)
    series = [v for v in fill_series(keep['Series']) if v['info']['season'] and v['info']['episode']]
    parts = movie_parts(keep['Películas'])
    later = {m for msgs in parts.values() for m in msgs[1:]}
    for v in keep['Películas']:
        if v['id'] in parts:  # la película entera se busca por su nombre sin «(1)» / «Parte 1»
            base = describe_full(dict(v, name=re.sub(r'(?i)(?:\(1\)|\b(?:parte?|part|pt|cd)\.?\s*1|^1_\d_)', ' ',
                                                       v.get('name') or '')))
            v['info'].update(title=base['title'] or v['info']['title'], year=base['year'] or v['info']['year'])
    movies = [v for v in keep['Películas'] if v['info']['title'] and v['id'] not in later]
    keys_m = list({(v['info']['title'], v['info'].get('alt'), v['info']['year']) for v in movies})
    keys_s = list({_show_key(v['info']) for v in series if v['info']['series']})
    found_m = dict(zip(keys_m, pool_map(lambda k: find_movie(search, *k), keys_m)))
    found_s = dict(zip(keys_s, pool_map(lambda k: find_show(search, *k), keys_s)))
    out = {'titulos': {}, 'pelis': [], 'capitulos': [], 'sin_ficha': {}, 'muestra': [],
           'partes': [(m, first, n) for first, msgs in parts.items() for n, m in enumerate(msgs, 1)]}
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
    db.executemany('INSERT OR IGNORE INTO partes VALUES (?,?,?)', found.get('partes', []))
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
