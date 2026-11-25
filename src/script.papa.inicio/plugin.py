# -*- coding: utf-8 -*-
"""Listas del asistente para las filas de la skin.

plugin://script.papa.inicio/?lista=favoritos  los favoritos de Kodi con su fanart y ficha de TMDb
plugin://script.papa.inicio/?run=<orden>      ejecuta la orden de un favorito que no es carpeta ni vídeo
plugin://script.papa.inicio/?telegram=actualizar  añade ya al catálogo lo nuevo del grupo de Telegram
plugin://script.papa.inicio/?precalentar=ya       prepara ya en AllDebrid lo que sale en las filas
plugin://script.papa.inicio/?fila=<lista>     una fila de Palantir desde su copia (filas.py)
plugin://script.papa.inicio/?buscar=<todo|peliculas|series>&q=<texto>  resultados de la lupa (lupa.py; catalogo.py de reserva)
plugin://script.papa.inicio/?play=<peliculas|series>&tmdb=…  reproduce por Balandro (fichas.py, balandro.py)
plugin://script.papa.inicio/?serie=<tmdb>  temporadas · ?temporada=<n>&fuente=…  capítulos (series.py)
plugin://script.papa.inicio/?genero=<peliculas|series>&fuente=…  un género de la fila «Géneros» (balandro.py)
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
import sys
import threading
import time
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import arte_deportes
from resources.lib import balandro
from resources.lib import calidad
from resources.lib import catalogo
from resources.lib import debrid
from resources.lib import favoritos as fv
from resources.lib import fichas
from resources.lib import filas
from resources.lib import historial
from resources.lib import series
from resources.lib import torrentio
from resources.lib import kodi_setup as ks
from resources.lib import lupa
from resources.lib import palantir
from resources.lib import pegar
from resources.lib import pelis
from resources.lib import telegram

FAVOURITES = 'special://profile/favourites.xml'
CACHE = ks.PROFILE + 'favoritos_tmdb.json'
BASE = 'plugin://%s/' % ks.ADDON_ID


def http_get(url, timeout=5):
    with urlopen(Request(url, headers={'User-Agent': 'Kodi'}), timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _load_cache():
    try:
        return json.loads(ks.read_file(CACHE) or '{}')
    except ValueError:
        return {}


def _item(fav, info):
    li = xbmcgui.ListItem(fav['name'], offscreen=True)
    art = {'thumb': fav['thumb'], 'icon': fav['thumb'], 'poster': fav['thumb']}
    tag = li.getVideoInfoTag()
    if info:
        # Con el tipo y el id de TMDb, la skin y TMDb Helper lo tratan como las películas de Palantir (fondo, logo…).
        art['fanart'] = info['fanart']
        art['poster'] = fav['thumb'] or info['poster']
        tag.setMediaType('movie' if info['kind'] == 'movie' else 'tvshow')
        tag.setTitle(info['title'])
        if info['year']:
            tag.setYear(int(info['year']))
        tag.setPlot(info['plot'])
        tag.setUniqueIDs({'tmdb': str(info['tmdb_id'])}, 'tmdb')
        li.setProperty('tmdb_id', str(info['tmdb_id']))
    li.setArt(art)
    return li


def listar_favoritos(handle):
    cache = _load_cache()
    before = dict(cache)
    api_key = ks.setting('tmdb_key')
    for fav in fv.parse(ks.read_file(FAVOURITES)):
        info = fv.lookup(fav, api_key, http_get, cache)
        li = _item(fav, info)
        kind, path = fv.target(fav['action'])
        if kind == 'play':
            li.setProperty('IsPlayable', 'true')  # lo mismo que PlayMedia(ruta)
        elif kind == 'builtin':
            path = BASE + '?' + urlencode({'run': path})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=kind == 'folder')
    if cache != before:
        ks.write_file(CACHE, json.dumps(cache, ensure_ascii=False))
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


# Clave de filas.to_item()['info'] → método de InfoTagVideo (setInfo está obsoleto en Kodi 21).
SETTERS = {'title': ('setTitle', str), 'year': ('setYear', int), 'plot': ('setPlot', str),
           'rating': ('setRating', float), 'votes': ('setVotes', int), 'genre': ('setGenres', list),
           'duration': ('setDuration', int), 'mpaa': ('setMpaa', str), 'premiered': ('setPremiered', str),
           'studio': ('setStudios', list), 'country': ('setCountries', list), 'tagline': ('setTagLine', str),
           'originaltitle': ('setOriginalTitle', str), 'imdbnumber': ('setIMDBNumber', str),
           'tvshowtitle': ('setTvShowTitle', str), 'season': ('setSeason', int), 'episode': ('setEpisode', int),
           'trailer': ('setTrailer', str), 'director': ('setDirectors', list), 'mediatype': ('setMediaType', str)}


def _as(kind, value):
    if kind is list:
        return list(value) if isinstance(value, (list, tuple)) else [str(value)]
    try:
        return kind(value)
    except (TypeError, ValueError):
        return None


def _fila_item(item):
    li = xbmcgui.ListItem(item['label'], offscreen=True)
    li.setArt(item['art'])
    tag = li.getVideoInfoTag()
    for key, value in item['info'].items():
        name, kind = SETTERS.get(key, (None, None))
        value = _as(kind, value) if name else None
        if value is not None:
            getattr(tag, name)(value)
    if item['uniqueids']:
        default = 'tmdb' if 'tmdb' in item['uniqueids'] else next(iter(item['uniqueids']))
        tag.setUniqueIDs(item['uniqueids'], default)
    for name, value in item['properties'].items():
        li.setProperty(name, str(value))
    return li


def listar_fila(handle, key):
    path = filas.row_paths(ks.load_rutas()).get(key)
    cached = ks.load_fila(key)
    if path and not filas.usable(cached, path) and not path.startswith(balandro.BALANDRO):
        # Primera vez (o la lista cambió): se pide ahora y se guarda. Las de Balandro no: cada página tarda ~15 s y
        # la fila esperaría; las rellena el servicio por detrás (filas.Refresher) y mientras sale vacía.
        files = ks.fetch_row(path)
        if filas.keeps(files, key):
            cached = filas.entry(path, files, time.time())
            ks.save_fila(key, cached)
    items = (cached or {}).get('items') or []
    if key.startswith('deportes.'):  # BlackGhost no trae fondos: los de TheSportsDB
        items = arte_deportes.apply(items, key, ks.load_arte())
    elif key in balandro.FILAS and (cached or {}).get('path', '').startswith(balandro.BALANDRO):
        kind = balandro.row_kind(cached['path'])
        if kind:  # nada por debajo de 1080p: solo lo que ya se sabe que lo tiene (calidad.py)
            pages = ks.load_calidades()
            items = [i for i in items if balandro.says_hd(i) or calidad.page_ok(kind, pages.get(balandro.page_url(i)))]
        items = balandro.fila(key, items)
    else:  # copia de Palantir (sin Balandro, o aún sin renovar): cada título se busca y se ve en Balandro
        items = [fichas.from_palantir(item) for item in items]
    year = time.localtime().tm_year
    if key in telegram.FILAS:  # «Estrenos», «Recién añadidas» y «Nuevos episodios»: también lo último del grupo
        kind = telegram.FILAS[key]
        since = year - 1 if key == 'peliculas.estrenos' else None
        items = telegram.mix(items, lupa.to_items(kind, telegram.newest(xbmcvfs.translatePath(ks.TELEGRAM), kind,
                                                                        since=since), limit=telegram.NEWEST))
    if key == 'peliculas.estrenos':  # solo las de este año (las de cualquier año, en «Recién añadidas»)
        items = balandro.this_year(items, year)
    for item in items:
        xbmcplugin.addDirectoryItem(handle, item['path'], _fila_item(item), isFolder=item['folder'])
    xbmcplugin.setContent(handle, filas.content(items))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def _buscar_tmdb(kind, text):
    """Resultados de TMDb para la lupa, o None si no hay clave o falla la red (entonces, el catálogo de Palantir)."""
    key = ks.setting('tmdb_key')
    if not key:
        return None
    items = []
    for k in lupa.kinds(kind):
        try:
            items += lupa.to_items(k, http_get(lupa.search_url(k, text, key)).get('results'))
        except Exception as exc:
            ks.log('lupa TMDb: %s' % exc)
            return None
    return items


def listar_busqueda(handle, kind, text):
    """Una fila de la búsqueda de la skin: TMDb (al día) o, de reserva, el catálogo de Palantir."""
    start = time.time()
    items = _buscar_tmdb(kind, text) if len(text.strip()) >= lupa.MIN_CHARS else []
    if items is None:
        items = catalogo.find(ks.palantir_db(), xbmcvfs.translatePath(ks.CATALOGO), kind, text)
    for item in items:
        xbmcplugin.addDirectoryItem(handle, item['path'], _fila_item(item), isFolder=item['folder'])
    xbmcplugin.setContent(handle, filas.content(items))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    ks.log('buscar %s %r: %d en %.2fs' % (kind, text, len(items), time.time() - start))


BALANDRO_CHANNELS = 'special://home/addons/plugin.video.balandro/channels/%s.json'
FUENTES = ks.PROFILE + 'fuentes_cast/'  # lo encontrado en Balandro por ficha (balandro.MAX_AGE): torrents en castellano
TMDB_CACHE = ks.PROFILE + 'tmdb/'  # fichas de TMDb para el arte de series, temporadas y películas
TMDB_MAX_AGE = 7 * 86400
MAX_PAGES = 8  # «Siguientes…» de Balandro que se siguen en una temporada
SEARCH_PAGES = 3  # páginas de resultados de cada búsqueda
TORRENTIO_TRIES = 3  # torrents de Torrentio que se comprueban en AllDebrid (~1 s cada uno)


def _json(path, default=None):
    try:
        return json.loads(ks.read_file(path) or 'null') or default
    except ValueError:
        return default


def _channel(cache):
    def info(channel_id):
        if channel_id not in cache:
            cache[channel_id] = balandro.channel_info(ks.read_file(BALANDRO_CHANNELS % channel_id))
        return cache[channel_id]
    return info


def _tmdb(name, url):
    """Una ficha de TMDb, guardada una semana. {} sin clave o sin red."""
    path = TMDB_CACHE + name + '.json'
    entry = _json(path)
    if entry and time.time() - entry.get('time', 0) < TMDB_MAX_AGE:
        return entry['data']
    try:
        data = http_get(url)
    except Exception as exc:
        ks.log('TMDb %s: %s' % (name, exc))
        return (entry or {}).get('data') or {}
    ks.write_file(path, json.dumps({'time': time.time(), 'data': data}, ensure_ascii=False))
    return data


def _show(tmdb):
    key = ks.setting('tmdb_key')
    return _tmdb('tv_%s' % tmdb, series.show_url(tmdb, key)) if key else {}


def _season(tmdb, season):
    key = ks.setting('tmdb_key')
    return _tmdb('tv_%s_%s' % (tmdb, season), series.season_url(tmdb, season, key)) if key else {}


def _movie_art(tmdb):
    key = ks.setting('tmdb_key')
    if not key:
        return {}, {}
    data = _tmdb('movie_%s' % tmdb, 'https://api.themoviedb.org/3/movie/%s?%s' % (
        tmdb, urlencode({'api_key': key, 'language': 'es-ES'})))
    return series.show_art(data), {'plot': data.get('overview')} if data.get('overview') else {}


def _fuentes(kind, tmdb, title, year, full=True):
    """Dónde ver una ficha en Balandro: lo guardado, si no web a web (FAST) hasta la primera que la tiene y, si
    ninguna y full, en todas (~15 s; sin full cuando Palantir la tiene de reserva)."""
    cache_path = '%s%s_%s.json' % (FUENTES, kind, tmdb)
    entry = _json(cache_path)
    if balandro.fresh(entry, time.time()):
        return entry['sources']
    channel = _channel({})
    searches = [balandro.search_url(kind, title, ch) for ch in balandro.FAST[kind]]
    if full:
        searches.append(balandro.search_url(kind, title))
    found = []
    for n, url in enumerate(searches):
        if full and n == len(searches) - 1:
            ks.notify('Buscando «%s» en más webs…' % title, 15000)
        start = time.time()
        files = ks.fetch_row(url) or []
        following = balandro.next_page(files)
        for _ in range(SEARCH_PAGES - 1):  # DonTorrent da los resultados por páginas (cada temporada y calidad cuenta)
            if not following:
                break
            more = ks.fetch_row(following) or []
            following = balandro.next_page(more)
            files += more
        found = balandro.sources(files, tmdb, title, year, channel)
        ks.log('balandro %s %r en %s: %d en %.1fs' % (kind, title, balandro.decode(url)['channel'], len(found),
                                                    time.time() - start))
        if found:
            ks.write_file(cache_path, json.dumps({'time': time.time(), 'sources': found}, ensure_ascii=False))
            break
    return found


def _listing(path):
    """Temporadas y capítulos de una página de Balandro, siguiendo sus «Siguientes…»."""
    listing = series.parse_listing(ks.fetch_row(path) or [])
    pages = 0
    while listing['next'] and pages < MAX_PAGES:
        pages += 1
        more = series.parse_listing(ks.fetch_row(listing['next']) or [])
        listing = {'seasons': listing['seasons'] + more['seasons'], 'episodes': listing['episodes'] + more['episodes'],
                   'next': more['next']}
    return listing


def _episode_paths(tmdb, title, year, season, episode):
    """Dónde ver un capítulo en Balandro, solo en 1080p o más: (rutas, temporada, capítulo). De la temporada marcada
    1080p/4K (DonTorrent) o con un tamaño de 1080p para su duración (PasateATorrent)."""
    found = _fuentes('series', tmdb, title, year, full=False)
    for channel in dict.fromkeys(s['channel'] for s in found):
        for page in series.seasons_from_sources([s for s in found if s['channel'] == channel]):
            if page['season'] != season:
                continue
            listed = [x for x in _listing(page['path'])['episodes'] if (x['season'], x['episode']) == (season, episode)]
            if listed and (page['hd'] or calidad.episode_hd(
                    listed[0].get('size'), series.runtime(_show(tmdb), _season(tmdb, season), episode))):
                return [listed[0]['path']], season, episode
    return [], season, episode


def _hd_movies(paths):
    """Fuentes de una película que llegan a 1080p: PasateATorrent lo dice en su página (calidades.json) y DonTorrent
    en el título o la dirección («[4K]», «1080p»). Las de otras webs siguen: el arreglo de Balandro (patches.py)
    descarta allí lo que no sea 1080p."""
    items = {path: balandro.decode(path) or {} for path in paths}
    pasate = [i.get('url') for i in items.values() if 'pasateatorrent' in (i.get('url') or '')]
    pages = ks.load_calidades()
    if ks.check_pages('peliculas', pasate, pages, time.time(), workers=4):
        ks.save_calidades(pages)

    def ok(item):
        url = item.get('url') or ''
        if url in pasate:
            return calidad.page_ok('peliculas', pages.get(url))
        if item.get('channel') == 'dontorrents':
            return calidad.is_hd(item.get('title') or '') or calidad.is_hd(url)
        return True
    return [path for path in paths if ok(items[path])]


def _dontorrent_torrent(page, content_id, tabla):
    """El .torrent de DonTorrent: su web pide resolver un reto (api_validate_pow.php), como hace Balandro."""
    found = re.match(r'(https?://[^/]+)', page or '')
    if not found or not content_id:
        return ''
    host, api = found.group(1), found.group(1) + '/api_validate_pow.php'
    challenge = ks.post_json(api, {'action': 'generate', 'content_id': str(content_id), 'tabla': tabla,
                                   'unescape': 'False'}, page).get('challenge')
    if not challenge:
        return ''
    url = ks.post_json(api, {'action': 'validate', 'challenge': challenge, 'nonce': str(debrid.pow_nonce(challenge)),
                             'unescape': 'False'}, page).get('download_url') or ''
    return host + url if url.startswith('/') else ('https:' + url if url.startswith('//') else url)


def _alldebrid():
    """El resolutor de AllDebrid de ResolveURL si hay cuenta vinculada (token), o None."""
    try:
        from resolveurl.plugins.alldebrid import AllDebridResolver
        resolver = AllDebridResolver()
    except Exception as exc:
        ks.log('AllDebrid no disponible: %s' % exc)
        return None
    return resolver if resolver.get_setting('enabled') == 'true' and resolver.get_setting('token') else None


def _torrents(kind, paths):
    """Los .torrent de 1080p o más de las fuentes, en su orden: de la página de cada película de PasateATorrent
    (calidades.json), el del capítulo (Balandro lo trae en su url) o el de DonTorrent (con su reto)."""
    items = [balandro.decode(path) or {} for path in paths]
    cache = ks.load_calidades()
    pasate = [i.get('url') for i in items if kind == 'peliculas' and 'pasateatorrent' in (i.get('url') or '')]
    if ks.check_pages('peliculas', pasate, cache, time.time(), workers=4):
        ks.save_calidades(cache)
    out = []
    for item in items:
        url = item.get('url') or ''
        if item.get('channel') == 'dontorrents':
            content_id = item.get('id') or (re.search(r'data-content-id="(\d+)"', ks.fetch_text(url)) or [None, None])[1]
            found = [_dontorrent_torrent(url, content_id, 'series' if kind == 'series' else 'peliculas')]
        elif '.torrent' in url or 'download_tt' in url:
            found = [url]
        else:
            found = debrid.hd_links((cache.get(url) or {}).get('links'))
        out += [u for u in found if u and u not in out]
    return out


def _prepare(resolver, btih, title):
    """Pide a AllDebrid que se baje el torrent a su nube por detrás, sin esperar (puede tardar minutos si lo comparte
    poca gente). La próxima vez que se pulse ya lo tendrá y arrancará en segundos."""
    from resolveurl.plugins import alldebrid
    try:
        resolver.net.http_POST(alldebrid.api_url + '/magnet/upload', form_data={'magnets': debrid.magnet(btih, title)},
                               headers=resolver.headers)
        return True
    except Exception as exc:
        ks.log('AllDebrid preparar %s: %s' % (btih[:8], exc))
        return False


def _hashes(torrents):
    """Los btih de unos .torrent (se descargan; los que no lo son se saltan)."""
    out = []
    for url in torrents[:6]:
        btih = debrid.info_hash(ks.fetch_bytes(url))
        if btih and btih not in out:
            out.append(btih)
    return out


def _cached(resolver, hashes, title):
    """Enlace directo de AllDebrid del primer torrent que ya tenga en su nube (arranca en segundos), o None."""
    for btih in hashes:
        try:
            return resolver.get_media_url('', debrid.magnet(btih, title), cached_only=True)
        except Exception as exc:
            ks.log('AllDebrid %s: %s' % (btih[:8], exc))
    return None


def _debrid_link(resolver, torrents, title):
    """(enlace, preparando) para unos .torrent: el que AllDebrid ya tenga o, si ninguno, le pide el primero por
    detrás (preparando=True): la tele nunca se queda esperando la descarga."""
    hashes = _hashes(torrents)
    link = _cached(resolver, hashes, title)
    if link:
        return link, False
    return None, bool(hashes) and _prepare(resolver, hashes[0], title)


def _imdb(kind, tmdb):
    """El id de IMDb de una ficha (Torrentio busca por él), de TMDb y guardado."""
    key = ks.setting('tmdb_key')
    if not key or not str(tmdb).isdigit():
        return ''
    path = 'tv' if kind == 'series' else 'movie'
    data = _tmdb('%s_%s_ids' % (path, tmdb), 'https://api.themoviedb.org/3/%s/%s/external_ids?api_key=%s' % (
        path, tmdb, key))
    return data.get('imdb_id') or ''


def _torrentio(kind, tmdb, season, episode):
    """Los torrents de Torrentio en castellano de 1080p o más ([{btih, quality, …}], el mejor primero)."""
    imdb = _imdb(kind, tmdb)
    if not imdb:
        return []
    try:
        streams = http_get(torrentio.stream_url(kind, imdb, season, episode)).get('streams')
    except Exception as exc:
        ks.log('Torrentio %s: %s' % (imdb, exc))
        return []
    found = torrentio.best(streams)
    ks.log('Torrentio %s %s %s: %s' % (kind, imdb, (season, episode) if season else '',
                                      [b['quality'] for b in found]))
    return found


def _palantir(kind, tmdb):
    """La ficha de Palantir de reserva (si sigue instalado y tiene enlaces del título), o None."""
    if not ks.has_addon('plugin.video.palantir3'):
        return None
    row = catalogo.palantir_row(ks.palantir_db(), kind, tmdb)
    return catalogo.palantir_path(kind, row) if row else None


def _sin_1080(title, preparing):
    ks.notify('«%s» se está preparando en AllDebrid: vuelve a pulsarlo en unos minutos' % title if preparing
              else '«%s» no está en 1080p en castellano' % title, 10000)


def _catalog_link(resolver, kind, tmdb, season, episode):
    """Enlace directo de un título del catálogo de Palantir: su fichero de 1fichier desbloqueado con AllDebrid, como
    hacía Palantir (palantir.py). Arranca al momento. None si no está en el catálogo o ningún enlace responde."""
    for link in palantir.best(catalogo.links(ks.palantir_db(), kind, tmdb, season, episode))[:4]:
        url = palantir.decrypt(link['link'])
        if not url:
            continue
        try:
            return resolver.get_media_url('', url)
        except Exception as exc:
            ks.log('catálogo %s %s: %s' % (kind, tmdb, exc))
    return None


def _art_info(kind, tmdb, season, episode):
    if kind == 'series':
        art = series.show_art(_show(tmdb))
        ep = next((x for x in (_season(tmdb, season) or {}).get('episodes') or []
                   if x.get('episode_number') == episode), {})
        if ep.get('still_path'):
            art['thumb'] = series.IMAGES + 'w780' + ep['still_path']
        return art, ({'plot': ep['overview']} if ep.get('overview') else {})
    return _movie_art(tmdb)


def _play(handle, playing, target, art, info):
    """Apunta lo que va a sonar (historial.Tracker) y se lo pasa a Kodi."""
    kind, title = playing['kind'], playing['title']
    xbmcgui.Window(10000).setProperty(historial.PENDING, json.dumps(playing, ensure_ascii=False))
    ks.log('reproducir %s %r %s: %s' % (kind, title, (playing['season'], playing['episode']) if playing['season']
                                        else '', playing['fuente'][:90]))
    li = _fila_item({'label': title, 'art': art, 'uniqueids': {'tmdb': playing['tmdb']}, 'properties': {},
                     'info': dict(title=title, mediatype='episode' if kind == 'series' else 'movie',
                                  **({'tvshowtitle': title, 'season': playing['season'],
                                      'episode': playing['episode']} if kind == 'series' else {}))})
    li.setPath(target)
    xbmcplugin.setResolvedUrl(handle, True, li)


def _pelis(kind, tmdb, season, episode):
    """Enlaces de PeLiS ya preparados en AllDebrid, en castellano y de 1080p o más ([{url, quality, size}]). Su
    dirección lleva la clave de AllDebrid cifrada: nunca se escribe en el log."""
    base = ks.setting(pegar.SETTING)
    imdb = _imdb(kind, tmdb) if base else ''
    if not imdb:
        return []
    try:
        streams = http_get(pelis.stream_url(base, kind, imdb, season, episode), timeout=15).get('streams')  # ~6 s
    except Exception as exc:
        ks.log('PeLiS %s: %s' % (imdb, type(exc).__name__))
        return []
    found = pelis.best(streams)
    ks.log('PeLiS %s %s %s: %s' % (kind, imdb, (season, episode) if season else '', [b['quality'] for b in found]))
    return found


def _telegram(kind, tmdb, season, episode):
    """(dirección del addon de Telegram, grupo, versiones) si el título está en el catálogo del grupo, o None."""
    path = xbmcvfs.translatePath(ks.TELEGRAM)
    found = telegram.versions(path, kind, tmdb, season, episode)
    token = ks.read_file(telegram.TOKEN).strip() if found else ''
    group = telegram.peer(path) if token else None
    return (telegram.base(token), group, found) if group else None


def _telegram_prefetch(tg):
    """Que el addon de Telegram vaya bajando el principio del mejor vídeo mientras se pregunta a Torrentio/PeLiS."""
    base, group, found = tg

    def run():
        try:
            urlopen(telegram.prefetch_url(base, group, found[0]['msg']), timeout=5).read()
        except Exception as exc:
            ks.log('Telegram precarga: %s' % type(exc).__name__)
    threading.Thread(target=run, name='papa-telegram', daemon=True).start()


def _telegram_link(tg):
    """Lo que hay que reproducir del primer vídeo del grupo que responde (puede haberse borrado), o None. Una
    película partida en varios vídeos va como «stack://» con todas sus partes (si falta alguna, no vale)."""
    base, group, found = tg
    for v in found[:telegram.TRIES]:
        try:
            for msg in v.get('parts') or [v['msg']]:
                with urlopen(Request(telegram.stream_url(base, group, msg), headers={'Range': 'bytes=0-1'}),
                             timeout=20) as r:
                    if r.status not in (200, 206):
                        raise IOError(r.status)
            return telegram.play_target(base, group, v)
        except Exception as exc:
            ks.log('Telegram %s: %s' % (v['msg'], type(exc).__name__))
    return None


def reproducir(handle, p):
    """?play=: por orden (medido el 25/11/2026):
    1. lo que AllDebrid ya tenga en 1080p o más de Torrentio (2–4 s);
    2. PeLiS (lo antiguo y lo nuevo, ya en AllDebrid): aunque tarde en contestar, arranca antes que Telegram, que
       necesita 10–24 s más para abrir el vídeo (probado: esperar a PeLiS sale mejor que no esperarle);
    3. el grupo de Telegram (precargado desde el principio); si es de menos de 1080p, AllDebrid prepara por detrás el
       mejor torrent para la próxima vez;
    4. Balandro y el catálogo de Palantir; si nada está listo, AllDebrid prepara el mejor torrent y avisa.
    Sin AllDebrid: Telegram, Balandro tal cual o la ficha del addon de Palantir."""
    kind, tmdb, title, year = p.get('play'), p.get('tmdb', ''), p.get('titulo', ''), p.get('anio', '')
    season, episode = (int(p[k]) if p.get(k, '').isdigit() else None for k in ('t', 'e'))
    if kind == 'series':
        season, episode = season or 1, episode or 1
    now = time.time()
    playing = {'kind': kind, 'tmdb': tmdb, 'title': title, 'year': year, 'season': season, 'episode': episode,
               'time': now}
    resolver = _alldebrid()
    tg = _telegram(kind, tmdb, season, episode)  # el catálogo del grupo está en la caja: se sabe al momento
    if tg:
        _telegram_prefetch(tg)

    def play(target, fuente):
        art, info = _art_info(kind, tmdb, season, episode)
        _play(handle, dict(playing, fuente=fuente), target, art, info)

    tio = []
    if resolver:
        _imdb(kind, tmdb)  # una sola consulta a TMDb, que las dos búsquedas de abajo leen ya guardada
        pool = ThreadPoolExecutor(1)  # PeLiS tarda 6–11 s: se le pregunta a la vez que a Torrentio
        pending = pool.submit(_pelis, kind, tmdb, season, episode)
        pool.shutdown(wait=False)  # no se espera a PeLiS si no hace falta
        tio = _torrentio(kind, tmdb, season, episode)
        direct = _cached(resolver, [b['btih'] for b in tio][:TORRENTIO_TRIES], title)
        if direct:
            return play(direct, 'torrentio')
        found = pending.result()
        if found:
            return play(found[0]['url'], 'pelis')
    direct = _telegram_link(tg) if tg else None  # lo que no tienen Torrentio/PeLiS (o sin AllDebrid)
    if direct:
        if not telegram.has_hd(tg[2]):  # que se sepa por qué se ve peor; y la próxima vez, en 1080p si se puede
            better = bool(resolver and tio) and _prepare(resolver, tio[0]['btih'], title)
            ks.notify(telegram.low_quality_notice(title, tg[2][0].get('quality'), better), 8000)
        return play(direct, 'telegram')

    intentos = _json(ks.INTENTOS, {})
    last = intentos.get(historial.key(playing))
    paths = [p['fuente']] if p.get('fuente') else []
    reserve = _palantir(kind, tmdb) if kind == 'peliculas' and not resolver else None
    if not paths or balandro.failed(last, paths[0], now):  # sin página, o la que había no llegó a arrancar
        if kind == 'series':
            more, season, episode = _episode_paths(tmdb, title, year, season, episode)
            playing.update(season=season, episode=episode)
        else:
            more = _hd_movies([s['path'] for s in _fuentes(kind, tmdb, title, year, full=False)])
        paths += [x for x in more if x not in paths]
    chosen = balandro.pick(paths, intentos.get(historial.key(playing)), now)

    target, torrents = chosen, []
    if resolver:
        torrents = _torrents(kind, [chosen] + [x for x in paths if x != chosen]) if chosen else []
        target = _cached(resolver, _hashes(torrents), title) if torrents else None
        if not target:
            target = _catalog_link(resolver, kind, tmdb, season, episode)  # Palantir: sus ficheros se borran
            chosen = 'catálogo' if target else chosen
        if not target:  # nada listo: AllDebrid prepara el mejor por detrás
            best = tio[0]['btih'] if tio else (_hashes(torrents) or [None])[0]
            _sin_1080(title, bool(best) and _prepare(resolver, best, title))
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem(offscreen=True))
            return
    elif not target and reserve:  # sin AllDebrid: la ficha de Palantir, con su lista de enlaces
        ks.log('reproducir %s %r por Palantir' % (kind, title))
        xbmcplugin.setResolvedUrl(handle, True, xbmcgui.ListItem(path=reserve, offscreen=True))
        return
    if not target:
        _sin_1080(title, False)
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem(offscreen=True))
        return
    intentos = {k: v for k, v in intentos.items() if now - v.get('time', 0) < balandro.MAX_AGE}
    intentos[historial.key(playing)] = {'fuente': chosen, 'time': now, 'ok': False}
    ks.write_file(ks.INTENTOS, json.dumps(intentos))
    art, info = _art_info(kind, tmdb, season, episode)
    _play(handle, dict(playing, fuente=chosen), target, art, info)


def _list(handle, items, content):
    for item in items:
        xbmcplugin.addDirectoryItem(handle, item['path'], _fila_item(item), isFolder=item['folder'])
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def _hd_episodes(tmdb, show, episodes):
    """Solo los capítulos de 1080p: la web no dice su calidad, se deduce del tamaño y la duración (calidad.py)."""
    seasons = {}
    keep = []
    for e in episodes:
        if e['season'] not in seasons:
            seasons[e['season']] = _season(tmdb, e['season'])
        if calidad.episode_hd(e.get('size'), series.runtime(show, seasons[e['season']], e['episode'])):
            keep.append(e)
    return keep, seasons


def _palantir_seasons(handle, tmdb, title):
    """Las temporadas de Palantir de reserva (sus enlaces en 1080p y castellano). False si no la tiene."""
    path = _palantir('series', tmdb)
    files = ks.fetch_row(path) if path else None
    if not files:
        return False
    ks.notify('«%s»: por Palantir' % title, 4000)
    _list(handle, [filas.to_item(f) for f in files], 'seasons')
    return True


def _nothing(handle, title):
    ks.notify('«%s» no está en 1080p en castellano' % title, 8000)
    xbmcplugin.endOfDirectory(handle, succeeded=False)


def _episodes(handle, tmdb, title, year, episodes, show, hd=False):
    """Los capítulos de 1080p (todos si la temporada ya lo dice, hd); si no queda ninguno, Palantir o un aviso."""
    if hd:
        keep, seasons = episodes, {s: _season(tmdb, s) for s in {e['season'] for e in episodes}}
    else:
        keep, seasons = _hd_episodes(tmdb, show, episodes)
    if not keep:
        if not _palantir_seasons(handle, tmdb, title):
            _nothing(handle, title)
        return
    _list(handle, series.episode_items(tmdb, title, year, keep, show, seasons), 'episodes')


CATALOGO = 'catalogo'  # fuente de una temporada que sale del catálogo de Palantir (palantir.py)


def _catalog_episodes(tmdb, season, numbers):
    """Los capítulos de una temporada del catálogo con algún enlace en castellano de 1080p o más."""
    db = ks.palantir_db()
    return [{'season': season, 'episode': n, 'path': ''} for n in numbers
            if palantir.best(catalogo.links(db, 'series', tmdb, season, n))]


def _balandro_seasons(tmdb, title, year, full):
    """Temporadas de 1080p en castellano de la primera web de Balandro que las tiene ([{season, path, hd}])."""
    found = _fuentes('series', tmdb, title, year, full=full)
    for channel in dict.fromkeys(s['channel'] for s in found):
        seasons = series.seasons_from_sources([s for s in found if s['channel'] == channel])
        if seasons:
            return seasons
    return []


def listar_serie(handle, p):
    """?serie=: temporadas del catálogo de Palantir (se ven con AllDebrid, al momento) y, si TMDb dice que hay más
    (posteriores al catálogo, 12/11/2026) o no está en él, las de 1080p en castellano de Balandro."""
    tmdb, title, year = p['serie'], p.get('titulo', ''), p.get('anio', '')
    show = _show(tmdb)
    aired = series.tmdb_seasons(show, time.strftime('%Y-%m-%d')) if _alldebrid() else []
    if aired:  # como Netflix: todo lo emitido según TMDb; cada capítulo se busca al pulsarlo (Torrentio primero)
        if len(aired) > 1:
            _list(handle, series.season_items(tmdb, title, year, aired, show), 'seasons')
        else:
            _tmdb_episodes(handle, tmdb, title, year, aired[0]['season'], show)
        return
    cat = catalogo.episodes(ks.palantir_db(), tmdb) if _alldebrid() else {}
    seasons = [{'season': n, 'path': CATALOGO, 'hd': True} for n in sorted(cat)]
    if not cat or (show.get('number_of_seasons') or 0) > max(cat):
        seasons += [s for s in _balandro_seasons(tmdb, title, year, full=not cat) if s['season'] not in cat]
        seasons.sort(key=lambda s: s['season'])
    if not seasons:
        if not _palantir_seasons(handle, tmdb, title):  # sin AllDebrid: el addon de Palantir
            _nothing(handle, title)
        return
    if len(seasons) > 1:
        _list(handle, series.season_items(tmdb, title, year, seasons, show), 'seasons')
    elif seasons[0]['path'] == CATALOGO:
        n = seasons[0]['season']
        _episodes(handle, tmdb, title, year, _catalog_episodes(tmdb, n, cat[n]), show, hd=True)
    else:
        listing = _listing(seasons[0]['path'])
        if listing['seasons']:  # webs que dan primero las temporadas
            _list(handle, series.season_items(tmdb, title, year, listing['seasons'], show), 'seasons')
        else:
            _episodes(handle, tmdb, title, year, listing['episodes'], show, seasons[0]['hd'])


def _tmdb_episodes(handle, tmdb, title, year, season, show):
    data = _season(tmdb, season)
    episodes = series.tmdb_episodes(data, season, time.strftime('%Y-%m-%d'))
    if not episodes:
        _nothing(handle, title)
        return
    _list(handle, series.episode_items(tmdb, title, year, episodes, show, {season: data}), 'episodes')


def listar_temporada(handle, p):
    tmdb, title, year, season = p['tmdb'], p.get('titulo', ''), p.get('anio', ''), int(p['temporada'])
    if p.get('fuente') == series.TMDB_SOURCE:
        _tmdb_episodes(handle, tmdb, title, year, season, _show(tmdb))
        return
    if p.get('fuente') == CATALOGO:
        numbers = catalogo.episodes(ks.palantir_db(), tmdb).get(season, [])
        _episodes(handle, tmdb, title, year, _catalog_episodes(tmdb, season, numbers), _show(tmdb), hd=True)
        return
    listed = _listing(p['fuente'])['episodes']
    _episodes(handle, tmdb, title, year, [e for e in listed if e['season'] == season] or listed, _show(tmdb),
              bool(p.get('hd')))


def listar_genero(handle, p):
    """?genero=: la lista de un género de la web, como fichas que se ven al pulsarlas; «Siguientes» al final."""
    kind = p['genero']
    files = ks.fetch_row(p['fuente']) or []
    items = [filas.to_item(f) for f in files]
    if balandro.row_kind(p['fuente']) == 'peliculas':  # nada por debajo de 1080p (calidad.py)
        pages = ks.load_calidades()
        if ks.check_pages(kind, [balandro.page_url(i) for i in items], pages, time.time(), workers=8):
            ks.save_calidades(pages)
        items = [i for i in items if calidad.page_ok(kind, pages.get(balandro.page_url(i)))]
    items = balandro.row_items(items, kind)
    following = series.parse_listing(files)['next']
    if following:
        items.append({'label': 'Siguientes…', 'folder': True, 'art': {}, 'info': {'title': 'Siguientes…'},
                      'uniqueids': {}, 'properties': {},
                      'path': fichas.papa_url([('genero', kind), ('titulo', p.get('titulo', '')),
                                               ('fuente', following)])})
    _list(handle, items, 'movies' if kind == 'peliculas' else 'tvshows')


def main(argv):
    handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip('-').isdigit() else -1
    params = {k: v[0] for k, v in parse_qs((argv[2] if len(argv) > 2 else '').lstrip('?')).items()}
    if params.get('telegram') == 'actualizar':  # lo nuevo del grupo ya, sin esperar a la madrugada
        ks.notify('Telegram: %s' % (ks.telegram_update(force=True) or 'no se pudo actualizar'), 8000)
        return
    if params.get('precalentar') == 'ya':  # lo de las filas, preparado ya en AllDebrid
        ks.notify('AllDebrid: %s' % (ks.prewarm() or 'no se pudo'), 8000)
        return
    if params.get('run'):
        xbmc.executebuiltin(params['run'])
    elif params.get('lista') == 'favoritos':
        listar_favoritos(handle)
    elif params.get('genero'):
        listar_genero(handle, params)
    elif params.get('play'):
        reproducir(handle, params)
    elif params.get('serie'):
        listar_serie(handle, params)
    elif params.get('temporada'):
        listar_temporada(handle, params)
    elif params.get('buscar'):
        listar_busqueda(handle, params['buscar'], params.get('q', ''))
    elif params.get('fila'):
        listar_fila(handle, params['fila'])
    elif handle >= 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False)


if __name__ == '__main__':
    main(sys.argv)
