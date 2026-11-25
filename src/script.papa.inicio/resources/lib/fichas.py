# -*- coding: utf-8 -*-
"""Las direcciones del asistente para ver una ficha: ?play= (película o capítulo, reproducible) y ?serie= (carpeta con
las temporadas). Las usan la lupa, las filas y el historial; plugin.py las atiende con Balandro. Puro."""
from urllib import parse

PAPA = 'plugin://script.papa.inicio/?'


def papa_url(params):
    return PAPA + parse.urlencode([(k, v) for k, v in params if v not in (None, '')])


def play_url(kind, tmdb, title, year='', season=None, episode=None, fuente=''):
    """Película o capítulo: al pulsar se busca en Balandro (o se usa fuente, su página ya conocida) y se reproduce."""
    return papa_url([('play', kind), ('tmdb', tmdb), ('titulo', title), ('anio', year), ('t', season), ('e', episode),
                     ('fuente', fuente)])


def serie_url(tmdb, title, year=''):
    return papa_url([('serie', tmdb), ('titulo', title), ('anio', year)])


def from_palantir(item):
    """Una ficha de las filas copiadas de Palantir (forma de filas.to_item) que, en vez de abrir Palantir, se ve por el
    asistente. Lo que no es película o serie con id de TMDb (carpetas de géneros…) queda igual."""
    tmdb = (item.get('uniqueids') or {}).get('tmdb')
    kind = {'movie': 'peliculas', 'tvshow': 'series'}.get((item.get('info') or {}).get('mediatype'))
    if not tmdb or not kind:
        return item
    info = item.get('info') or {}
    title, year = info.get('title') or item.get('label', ''), info.get('year') or ''
    if kind == 'peliculas':
        return dict(item, path=play_url(kind, tmdb, title, year), folder=False,
                    properties=dict(item.get('properties') or {}, IsPlayable='true'))
    props = {k: v for k, v in (item.get('properties') or {}).items() if k != 'IsPlayable'}
    return dict(item, path=serie_url(tmdb, title, year), folder=True, properties=props)
