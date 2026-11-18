# -*- coding: utf-8 -*-
"""Encuentra en la caja las carpetas de Palantir y BlackGhost que forman el menú.

Todo lo que toca Kodi llega inyectado (list_dir, find_addon, ask), así que este
módulo es puro y se prueba sin Kodi.
"""
import re
import unicodedata

TAG_RE = re.compile(r'\[/?[A-Za-z]+(?:[ =][^\]]*)?\]')


def clean(label):
    """Etiqueta legible: sin marcas [COLOR]/[B] de Kodi, con acentos."""
    return ' '.join(TAG_RE.sub(' ', label or '').split())


def normalize(label):
    text = unicodedata.normalize('NFKD', clean(label))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def _has(text, keyword):
    return re.search(r'(?:^| )' + re.escape(normalize(keyword)), text) is not None


def matches(label, keywords, exclude=()):
    text = normalize(label)
    if any(_has(text, x) for x in exclude):
        return False
    return any(_has(text, k) for k in keywords)


def _cat(label, keywords, exclude=()):
    return {'label': label, 'keywords': list(keywords), 'exclude': list(exclude)}


PALANTIR_ROOT = {
    'peliculas': _cat('Películas', ['pelicula', 'peli', 'movie', 'cine']),
    'series': _cat('Series', ['serie', 'tv show', 'tvshow', 'shows']),
}

# Listas de Palantir que solo funcionan con una cuenta de Trakt.tv: sin ella preguntan "¿desea activarla ahora?",
# luego "No se han encontrado resultados", y los avisos bloquean el mando (Palantir 3.3.11, noviembre de 2026).
TRAKT_ONLY = ['mas vistas', 'recomendad', 'seguimiento', 'trakt']


BUSCAR_POR_TITULO = [r'^por titulo']


def needs_trakt(label):
    return matches(label, TRAKT_ONLY)


PELICULAS = {
    'estrenos': _cat('Estrenos', ['estreno', 'en cines', 'cartelera', 'novedad', 'ultimas', 'recien'],
                     exclude=TRAKT_ONLY + ['anadid']),
    'recientes': _cat('Recién añadidas', ['anadid', 'recently added'], exclude=TRAKT_ONLY),
    'populares': _cat('Populares', ['popular', 'tendencia', 'trending'], exclude=TRAKT_ONLY),
    'valoradas': _cat('Mejor valoradas', ['valorad', 'mejor', 'top'], exclude=TRAKT_ONLY),
    'generos': _cat('Géneros', ['genero', 'categoria'], exclude=TRAKT_ONLY),
}

SERIES = {
    'novedades': _cat('Novedades', ['novedad', 'estreno', 'nuevos episodios', 'ultimos episodios', 'ultimas'],
                      exclude=TRAKT_ONLY),
    'nuevas': _cat('Nuevas series', ['nuevas series', 'series nuevas', 'nueva serie'], exclude=TRAKT_ONLY),
    'emision': _cat('En emisión', ['emision', 'en antena', 'airing', 'al aire'], exclude=TRAKT_ONLY),
    'populares': _cat('Populares', ['popular', 'tendencia', 'trending'], exclude=TRAKT_ONLY),
    'valoradas': _cat('Mejor valoradas', ['valorad', 'mejor', 'top'], exclude=TRAKT_ONLY),
    'generos': _cat('Géneros', ['genero', 'categoria'], exclude=TRAKT_ONLY),
}

# --- BlackGhost 8.0.66 (noviembre de 2026) ---
# No tiene una carpeta por deporte: ordena por fuentes (decenas de "agendas" y listas de canales). Con el código
# guardado en codeservernew.txt, "INGRESAR AL ADDON" lleva sin preguntar a Deportes, Agendas + Canales Acestream…
BLACKGHOST_ENTRAR = {'entrar': _cat('Entrar', ['ingresar'])}
BLACKGHOST_MENU = {
    'deportes': _cat('Deportes', ['deporte', 'sport']),
    'acestream': _cat('Agendas + Canales Acestream', ['acestream', 'agendas canales']),
}

# Etiquetas de las filas de Deportes; el orden del menú está en menus.ORDEN_DEPORTES.
DEPORTES = {
    'agenda': _cat('Agenda de hoy', []),
    'espana': _cat('Partidos en España', []),
    'futbol': _cat('Fútbol', []),
    'baloncesto': _cat('Baloncesto', []),
    'nfl': _cat('NFL', []),
    'motor': _cat('Motor: F1 y MotoGP', []),
    'f1': _cat('Fórmula 1 en español', []),
    'ufc': _cat('UFC y boxeo', []),
    'canales': _cat('Canales Acestream', []),
}

# Dentro de "AGENDA NSPORTS" sí hay una carpeta por deporte. El orden es la prioridad al emparejar.
NSPORTS = {
    'nfl': _cat('NFL', ['nfl', 'futbol americano', 'american football']),
    'futbol': _cat('Fútbol', ['futbol', 'soccer'], exclude=['americano', 'sala']),
    'baloncesto': _cat('Baloncesto', ['baloncesto', 'basket', 'nba']),
    'motor': _cat('Motor', ['motorsport', 'motor', 'formula 1', 'motogp']),
    'ufc': _cat('UFC y boxeo', ['ufc', 'mma', 'boxeo', 'box']),
}

# Por su nombre, de la preferida a la de reserva. "DEPORTESPLUS" sin "+" va en hora de España (la "+" en la latina).
AGENDA = [r'^agenda deportesplus st', r'^agenda live', r'^agenda']
AGENDA_NSPORTS = [r'^agenda nsports']
F1_ESPANOL = [r'^formula 1 replays']
PARTIDOS_ESPANA = [r'^agenda del dia ciraco', r'^agenda del dia']  # CIRACO: los de las teles de España
CANALES_ACESTREAM = [r'^acestream\W* mixto', r'^acestream\W* ks']


def _plain_label(label):
    """Como normalize, pero conserva "+" (DEPORTESPLUS+ es otra agenda)."""
    text = unicodedata.normalize('NFKD', clean(label))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return ' '.join(re.sub(r'[^a-z0-9+]+', ' ', text).split())


def find_first(entries, patterns):
    """La primera carpeta cuyo nombre encaja con el primer patrón que encaje con alguna."""
    folders = _folders(entries)
    for pattern in patterns:
        for e in folders:
            if re.search(pattern, _plain_label(e['label'])):
                return _item(e)
    return None


def _folders(entries):
    return [e for e in entries or [] if e.get('filetype', 'directory') == 'directory']


def _item(entry):
    return {'label': clean(entry['label']), 'path': entry['file']}


def classify(entries, catalog, used=None):
    """{clave: {'label', 'path'}} con la primera carpeta libre de cada categoría."""
    used = set() if used is None else used
    found = {}
    folders = _folders(entries)
    for key, cat in catalog.items():
        for e in folders:
            if e['file'] in used:
                continue
            if matches(e['label'], cat['keywords'], cat['exclude']):
                found[key] = _item(e)
                used.add(e['file'])
                break
    return found


def _ask_missing(found, keys, catalog, entries, used, ask, addon_name):
    for key in keys:
        if key in found:
            continue
        free = [e for e in _folders(entries) if e['file'] not in used]
        if not free:
            return
        labels = [clean(e['label']) for e in free]
        idx = ask('¿Qué carpeta de %s es %s?' % (addon_name, catalog[key]['label']), labels)
        if idx is not None and 0 <= idx < len(free):
            found[key] = _item(free[idx])
            used.add(free[idx]['file'])


def _root(addon_id):
    return 'plugin://%s/' % addon_id


def discover_palantir(list_dir, find_addon, ask):
    addon = find_addon(['palantir'])
    if not addon:
        return None
    entries = list_dir(_root(addon))
    used = set()
    top = classify(entries, PALANTIR_ROOT, used)
    _ask_missing(top, ['peliculas', 'series'], PALANTIR_ROOT, entries, used, ask, 'Palantir')
    result = {'id': addon, 'peliculas': {}, 'series': {}}
    search = {}
    for key, catalog in (('peliculas', PELICULAS), ('series', SERIES)):
        if key in top:
            entries = list_dir(top[key]['path'])
            result[key] = classify(entries, catalog)
            by_title = find_first(entries, BUSCAR_POR_TITULO)  # para la lupa (buscar.py); no es una fila
            if by_title:
                search[key] = by_title['path']
    if search:
        result['buscar'] = search
    return result


def discover_blackghost(list_dir, find_addon, ask):
    """{'id', 'agenda', 'deportes': {fila: carpeta}} de BlackGhost. Solo pregunta por la carpeta Deportes."""
    addon = find_addon(['black ghost', 'blackghost'])
    if not addon:
        return None
    menu = list_dir(_root(addon))
    entrar = classify(menu, BLACKGHOST_ENTRAR).get('entrar')
    if entrar:
        menu = list_dir(entrar['path'])
    used = set()
    top = classify(menu, BLACKGHOST_MENU, used)
    if _folders(menu) and 'deportes' not in top:
        _ask_missing(top, ['deportes'], BLACKGHOST_MENU, menu, used, ask, 'BlackGhost')
    result = {'id': addon, 'deportes': {}}
    rows = {}
    if 'deportes' in top:
        deportes = list_dir(top['deportes']['path'])
        rows['agenda'] = find_first(deportes, AGENDA)
        nsports = find_first(deportes, AGENDA_NSPORTS)
        if nsports:
            rows.update(classify(list_dir(nsports['path']), NSPORTS))
        rows['f1'] = find_first(deportes, F1_ESPANOL)
    if 'acestream' in top:
        acestream = list_dir(top['acestream']['path'])
        rows['espana'] = find_first(acestream, PARTIDOS_ESPANA)
        rows['canales'] = find_first(acestream, CANALES_ACESTREAM)
    agenda = rows.pop('agenda', None)
    if agenda:
        result['agenda'] = agenda
    result['deportes'] = {k: rows[k] for k in DEPORTES if rows.get(k)}
    return result
