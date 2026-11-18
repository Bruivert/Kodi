from urllib.parse import parse_qs, urlparse

from resources.lib import filas as fl

PAL = 'plugin://plugin.video.palantir3/'

RUTAS = {'palantir': {
    'peliculas': {'estrenos': {'label': 'Novedades', 'path': PAL + '?estrenos'},
                  'populares': {'label': 'Más vistas', 'path': PAL + '?trakt'},  # pide Trakt: nunca se copia
                  'generos': {'label': 'Por géneros', 'path': PAL + '?generos'}},
    'series': {'novedades': {'label': 'Últimas actualizaciones', 'path': PAL + '?novedades'}}},
    'blackghost': {'agenda': {'label': 'Agenda', 'path': 'plugin://bg/?agenda'},
                   'deportes': {'futbol': {'label': 'Fútbol', 'path': 'plugin://bg/?futbol'}}}}
PALANTIR_ONLY = {'palantir': RUTAS['palantir']}

# Lo que devuelve Files.GetDirectory de "Novedades" de Palantir 3.3.11 (17/11/2026), recortado.
MOVIE = {
    'label': '[COLOR ffffffff] No nos rendimos[/COLOR] [COLOR ffc0c0c0](2026)[/COLOR]',
    'title': '[COLOR ffffffff] No nos rendimos[/COLOR] [COLOR ffc0c0c0](2026)[/COLOR]',
    'file': PAL + '?x0SMx0iNy', 'filetype': 'file', 'type': 'movie', 'year': 2026,
    'art': {'fanart': 'image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2fw1280%2fumx.jpg/',
            'clearlogo': 'image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2fw500%2faxW.png/',
            'poster': 'image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2fw500%2f6cH.jpg/'},
    'customproperties': {'isplayable': 'true', 'p3calidad': '1080p', 'p3titulo': 'No nos rendimos'},
    'genre': ['Suspense', 'Acción'], 'imdbnumber': '1616687', 'uniqueid': {'tmdb': '1616687'},
    'mpaa': '16', 'plot': 'Un exsoldado…', 'premiered': '2026-11-12', 'rating': 7.0, 'runtime': 8220,
    'votes': '0', 'trailer': '', 'thumbnail': 'image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2fw500%2f6cH.jpg/',
}
SHOW = {'label': 'La isla de las tentaciones', 'title': 'La isla de las tentaciones', 'file': PAL + '?isla',
        'filetype': 'directory', 'type': 'tvshow', 'year': 2020, 'showtitle': 'La isla de las tentaciones',
        'uniqueid': {'tmdb': '95676'}, 'art': {}, 'customproperties': {'p3totalseasons': '7'},
        'trailer': 'plugin://plugin.video.youtube/play/?video_id=kszqhHJeuw4'}
GENRE = {'label': '[COLOR ffffd700]Acción[/COLOR]', 'file': PAL + '?accion', 'filetype': 'directory',
         'type': 'unknown', 'art': {'icon': 'image://special%3a%2f%2fhome%2faddons%2fx%2fbuscar.png/'}}


def test_rows_are_the_palantir_lists_without_trakt_and_the_blackghost_ones():
    assert fl.row_paths(RUTAS) == {'peliculas.estrenos': PAL + '?estrenos', 'peliculas.generos': PAL + '?generos',
                                   'series.novedades': PAL + '?novedades', 'deportes.agenda': 'plugin://bg/?agenda',
                                   'deportes.futbol': 'plugin://bg/?futbol'}
    assert fl.row_paths({}) == {}


def test_sports_are_renewed_more_often_than_films():
    # La agenda cambia a lo largo del día; las películas y series, de un día para otro.
    assert fl.max_age('deportes.agenda') < fl.max_age('peliculas.estrenos')
    assert fl.max_age('deportes.agenda') <= 15 * 60


def test_fila_url_points_to_the_assistant():
    url = urlparse(fl.fila_url('peliculas.estrenos'))
    assert (url.scheme, url.netloc) == ('plugin', 'script.papa.inicio')
    assert parse_qs(url.query) == {'fila': ['peliculas.estrenos']}


def test_unwrap_image_gives_the_real_address():
    assert fl.unwrap_image(MOVIE['art']['fanart']) == 'https://image.tmdb.org/t/p/w1280/umx.jpg'
    assert fl.unwrap_image('special://home/x.png') == 'special://home/x.png'
    assert fl.unwrap_image('') == ''


def test_movie_keeps_everything_kodi_and_the_trailer_service_use():
    item = fl.to_item(MOVIE)
    assert item['path'] == MOVIE['file'] and item['label'] == MOVIE['label']
    assert item['folder'] is False and item['properties']['IsPlayable'] == 'true'
    assert item['properties']['p3calidad'] == '1080p' and 'isplayable' not in item['properties']
    assert item['art']['fanart'] == 'https://image.tmdb.org/t/p/w1280/umx.jpg'
    assert item['art']['thumb'] == 'https://image.tmdb.org/t/p/w500/6cH.jpg'
    info = item['info']
    assert info['mediatype'] == 'movie' and info['title'] == MOVIE['title'] and info['year'] == 2026
    assert info['imdbnumber'] == '1616687' and info['genre'] == ['Suspense', 'Acción']
    assert info['duration'] == 8220 and info['rating'] == 7.0 and info['plot'] == 'Un exsoldado…'
    assert item['uniqueids'] == {'tmdb': '1616687'}


def test_series_and_folders_open_as_folders():
    show = fl.to_item(SHOW)
    assert show['folder'] is True and 'IsPlayable' not in show['properties']
    assert show['info']['mediatype'] == 'tvshow' and show['info']['tvshowtitle'] == 'La isla de las tentaciones'
    assert show['info']['trailer'] == SHOW['trailer']
    genre = fl.to_item(GENRE)
    assert genre['folder'] is True and 'mediatype' not in genre['info']
    assert genre['art']['icon'] == 'special://home/addons/x/buscar.png'


def test_content_type_follows_the_items():
    assert fl.content([fl.to_item(MOVIE)]) == 'movies'
    assert fl.content([fl.to_item(SHOW)]) == 'tvshows'
    assert fl.content([fl.to_item(MOVIE), fl.to_item(SHOW)]) == 'videos'
    assert fl.content([]) == 'videos'


def test_entry_is_usable_only_for_the_same_list():
    entry = fl.entry(PAL + '?estrenos', [MOVIE], now=1000)
    assert entry['path'] == PAL + '?estrenos' and entry['time'] == 1000 and len(entry['items']) == 1
    assert fl.usable(entry, PAL + '?estrenos')
    assert not fl.usable(entry, PAL + '?otra')  # el asistente volvió a buscar las listas y esta cambió
    assert not fl.usable(None, PAL + '?estrenos')
    assert fl.usable(fl.entry('plugin://bg/?agenda', [], now=1000), 'plugin://bg/?agenda')  # vacía también vale


def test_next_to_refresh_takes_the_missing_then_the_oldest_stale():
    rows = fl.row_paths(PALANTIR_ONLY)
    index = {'peliculas.estrenos': {'path': PAL + '?estrenos', 'time': 6000},
             'peliculas.generos': {'path': PAL + '?generos', 'time': 6500},
             'series.novedades': {'path': PAL + '?novedades', 'time': 9000}}
    assert fl.next_to_refresh(rows, index, now=9500) is None  # todas al día
    assert fl.next_to_refresh(rows, index, now=10000) == 'peliculas.estrenos'  # la más vieja
    del index['series.novedades']
    assert fl.next_to_refresh(rows, index, now=9500) == 'series.novedades'  # sin copia
    index['series.novedades'] = {'path': PAL + '?cambiada', 'time': 9400}
    assert fl.next_to_refresh(rows, index, now=9500) == 'series.novedades'  # la lista cambió


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def refresher(clock, fetch, can_run=lambda: True, index=None):
    saved = {}
    index = {} if index is None else index

    def save(key, entry):
        saved[key] = entry
        index[key] = {'path': entry['path'], 'time': entry['time']}
    r = fl.Refresher(lambda: fl.row_paths(PALANTIR_ONLY), lambda: index, fetch, save, can_run, clock)
    return r, saved


def test_refresher_waits_after_start_then_renews_one_list_at_a_time():
    clock, asked = Clock(1000), []
    r, saved = refresher(clock, lambda path: asked.append(path) or [MOVIE])
    assert r.tick() is None and asked == []  # recién encendida: deja arrancar a Kodi
    clock.t += fl.START_DELAY
    assert r.tick() == 'peliculas.estrenos' and asked == [PAL + '?estrenos']
    assert saved['peliculas.estrenos']['items'][0]['path'] == MOVIE['file']
    assert r.tick() is None  # una cada GAP segundos: Kodi ejecuta Python de uno en uno
    clock.t += fl.GAP
    assert r.tick() == 'peliculas.generos'
    clock.t += fl.GAP
    assert r.tick() == 'series.novedades'
    clock.t += fl.GAP
    assert r.tick() is None and len(asked) == 3  # todas al día
    clock.t += fl.MAX_AGE
    assert r.tick() == 'peliculas.estrenos'  # pasada la hora, otra vuelta


def test_refresher_does_not_run_while_watching_or_using_the_remote():
    clock, busy = Clock(1000), [True]
    r, saved = refresher(clock, lambda path: [MOVIE], can_run=lambda: not busy[0])
    clock.t += fl.START_DELAY
    assert r.tick() is None and saved == {}
    busy[0] = False
    assert r.tick() == 'peliculas.estrenos'


def test_refresher_backs_off_when_palantir_fails_and_keeps_the_old_copy():
    clock = Clock(10000)
    old = {key: {'path': path, 'time': 9000} for key, path in fl.row_paths(PALANTIR_ONLY).items()}
    old['peliculas.estrenos']['time'] = 0
    r, saved = refresher(clock, lambda path: [], index=old)  # Palantir sin red: lista vacía
    clock.t += fl.START_DELAY
    assert r.tick() == 'peliculas.estrenos' and saved == {}
    clock.t += fl.GAP
    assert r.tick() is None  # no insiste cada 20 s
    clock.t += fl.FAIL_WAIT
    assert r.tick() == 'peliculas.estrenos'


def test_next_to_refresh_uses_the_shorter_age_for_sports():
    rows = {'deportes.agenda': 'plugin://bg/?agenda', 'peliculas.estrenos': PAL + '?estrenos'}
    index = {'deportes.agenda': {'path': 'plugin://bg/?agenda', 'time': 0},
             'peliculas.estrenos': {'path': PAL + '?estrenos', 'time': 0}}
    assert fl.next_to_refresh(rows, index, now=fl.max_age('deportes.agenda')) == 'deportes.agenda'


def test_only_sports_lists_may_be_empty():
    # La agenda puede quedarse sin partidos (de madrugada, o con el código de BlackGhost caducado); "Estrenos" vacía
    # es que Palantir ha fallado.
    assert fl.keeps(None, 'deportes.agenda') is False  # fallo de red
    assert fl.keeps([], 'deportes.agenda') is True
    assert fl.keeps([], 'peliculas.estrenos') is False
    assert fl.keeps([MOVIE], 'peliculas.estrenos') is True


def test_refresher_saves_an_empty_agenda_instead_of_keeping_yesterdays():
    clock = Clock(10000)
    rows = {'deportes.agenda': 'plugin://bg/?agenda'}
    index = {'deportes.agenda': {'path': 'plugin://bg/?agenda', 'time': 0}}
    saved = {}
    r = fl.Refresher(lambda: rows, lambda: index, lambda path: [], lambda k, e: saved.__setitem__(k, e),
                     lambda: True, clock)
    clock.t += fl.START_DELAY
    assert r.tick() == 'deportes.agenda'
    assert saved['deportes.agenda']['items'] == []
    clock.t += fl.GAP
    assert r.next_time == clock.t  # no es un fallo: no espera los 5 minutos


def test_refresher_waits_on_a_network_failure():
    clock = Clock(10000)
    rows = {'deportes.agenda': 'plugin://bg/?agenda'}
    saved = {}
    r = fl.Refresher(lambda: rows, lambda: {}, lambda path: None, lambda k, e: saved.__setitem__(k, e),
                     lambda: True, clock)
    clock.t += fl.START_DELAY
    assert r.tick() == 'deportes.agenda' and saved == {}
    clock.t += fl.GAP
    assert r.tick() is None  # espera FAIL_WAIT
