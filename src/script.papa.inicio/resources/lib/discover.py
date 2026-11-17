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

DEPORTES_ROOT = {
    'deportes': _cat('Deportes', ['deporte', 'sport']),
}

# El orden es la prioridad al emparejar y el orden en que se ven en el menú.
DEPORTES = {
    'agenda': _cat('Agenda de hoy', ['agenda', 'hoy', 'directo', 'en vivo', 'calendario', 'programacion', 'live']),
    'nfl': _cat('NFL', ['nfl', 'futbol americano', 'american football', 'super bowl']),
    'futbol': _cat('Fútbol', ['futbol', 'soccer', 'laliga', 'la liga', 'champions', 'premier league'],
                   exclude=['americano', 'sala']),
    'baloncesto': _cat('Baloncesto', ['baloncesto', 'basket', 'nba', 'acb', 'euroliga', 'euroleague']),
    'padel': _cat('Pádel', ['padel']),
    'f1': _cat('Fórmula 1', ['formula 1', 'formula uno', 'formula1', 'f1']),
    'motogp': _cat('MotoGP', ['motogp', 'moto gp', 'motociclismo', 'motos', 'moto2', 'moto3']),
    'ufc': _cat('UFC', ['ufc', 'mma', 'artes marciales']),
}


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
    if 'peliculas' in top:
        result['peliculas'] = classify(list_dir(top['peliculas']['path']), PELICULAS)
    if 'series' in top:
        result['series'] = classify(list_dir(top['series']['path']), SERIES)
    return result


def discover_blackghost(list_dir, find_addon, ask):
    addon = find_addon(['black ghost', 'blackghost'])
    if not addon:
        return None
    root_entries = list_dir(_root(addon))
    root_used = set()
    top = classify(root_entries, DEPORTES_ROOT, root_used)
    _ask_missing(top, ['deportes'], DEPORTES_ROOT, root_entries, root_used, ask, 'BlackGhost')
    result = {'id': addon, 'deportes': {}}
    if 'deportes' not in top:
        return result
    entries = list_dir(top['deportes']['path'])
    used = set()
    sports = classify(entries, DEPORTES, used)
    sport_keys = [k for k in DEPORTES if k != 'agenda']
    _ask_missing(sports, sport_keys, DEPORTES, entries, used, ask, 'BlackGhost')
    agenda = sports.pop('agenda', None)
    if agenda is None:
        agenda = classify(root_entries, {'agenda': DEPORTES['agenda']}, root_used).get('agenda')
    result['deportes'] = {k: sports[k] for k in sport_keys if k in sports}
    if agenda:
        result['agenda'] = agenda
    return result
