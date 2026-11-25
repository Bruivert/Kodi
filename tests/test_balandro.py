import base64
import json
from urllib import parse

from resources.lib import balandro as bal


def _url(item):
    return 'plugin://plugin.video.balandro/?' + parse.quote(base64.b64encode(json.dumps(item).encode('utf-8')))


def _movie(channel, tmdb='1215185', title='La infiltrada', year=2024):
    info = {'year': year}
    if tmdb:
        info['tmdb_id'] = tmdb
    return {'file': _url({'channel': channel, 'action': 'findvideos', 'contentType': 'movie', 'contentTitle': title,
                          'infoLabels': info}), 'filetype': 'file'}


HEADER = {'file': 'plugin://plugin.video.balandro/?action=', 'filetype': 'directory'}

CHANNELS = {'pasateatorrent': {'name': 'PasateATorrent', 'torrent': True, 'cast': True},
            'mitorrent': {'name': 'MiTorrent', 'torrent': True, 'cast': False},
            'cuevana3pro': {'name': 'Cuevana3Pro', 'torrent': False, 'cast': True},
            'repelis28': {'name': 'RePelis28', 'torrent': False, 'cast': False}}


def test_search_url_is_balandros_own_item_with_the_title_already_typed():
    url = bal.search_url('peliculas', 'Amor & odio = 1')
    assert url.startswith('plugin://plugin.video.balandro/?')
    assert bal.decode(url) == {'channel': 'search', 'action': 'search', 'search_type': 'movie',
                               'buscando': 'Amor & odio = 1'}
    assert bal.decode(bal.search_url('series', 'X'))['search_type'] == 'tvshow'
    assert bal.decode(bal.search_url('peliculas', 'X', 'pasateatorrent'))['channel'] == 'pasateatorrent'


def test_fast_channels_are_spanish_torrents_that_say_their_quality():
    assert bal.FAST == {'peliculas': ('pasateatorrent', 'dontorrents'), 'series': ('dontorrents', 'pasateatorrent')}
    assert set(sum(bal.FAST.values(), ())) <= set(bal.CASTELLANO)


def test_by_default_only_spanish_torrent_webs_count():
    channels = dict(CHANNELS, pelispanda={'name': 'PelisPanda', 'torrent': True, 'cast': True},
                    dontorrents={'name': 'DonTorrent', 'torrent': True, 'cast': True})
    files = [_movie('cuevana3pro'), _movie('repelis28'), _movie('mitorrent'), _movie('pelispanda'),
             _movie('dontorrents'), _movie('pasateatorrent')]
    assert [s['channel'] for s in bal.sources(files, 1215185, 'La infiltrada', 2024, channels.get)] == [
        'dontorrents', 'pasateatorrent']


def test_page_url_is_the_webs_page():
    item = {'path': _url({'channel': 'pasateatorrent', 'action': 'findvideos', 'url': 'https://p.org/tony/'})}
    assert bal.page_url(item) == 'https://p.org/tony/' and bal.page_url({'path': 'x'}) == ''


def test_decode_ignores_what_is_not_a_balandro_item():
    assert bal.decode('plugin://plugin.video.balandro/?action=') is None
    assert bal.decode('plugin://plugin.video.balandro/') is None
    assert bal.decode('') is None


def test_only_results_of_the_chosen_title_torrents_in_spanish_first():
    files = [HEADER, _movie('repelis28'), _movie('cuevana3pro', tmdb='999', title='La La Land', year=2016),
             _movie('cuevana3pro'), _movie('mitorrent'), _movie('pasateatorrent'), _movie('desconocido')]
    found = bal.sources(files, 1215185, 'La infiltrada', 2024, CHANNELS.get, torrent_only=False)
    assert [s['channel'] for s in found] == ['pasateatorrent', 'mitorrent', 'cuevana3pro', 'repelis28', 'desconocido']
    assert found[0] == {'channel': 'pasateatorrent', 'name': 'PasateATorrent', 'torrent': True, 'other': '',
                        'path': files[5]['file'], 'folder': False, 'label': '', 'url': ''}
    assert found[-1]['name'] == 'desconocido' and found[-1]['torrent'] is False


def test_without_tmdb_the_title_and_year_must_match():
    files = [_movie('repelis28', tmdb=None, title='LA INFILTRADA', year=2025),
             _movie('mitorrent', tmdb=None, title='La infiltrada en la NASA'),
             _movie('cuevana3pro', tmdb=None, title='La infiltrada', year=2019),
             _movie('pasateatorrent', tmdb=None, title='La infiltrada', year=None)]
    found = bal.sources(files, '1215185', 'La infiltrada', 2024, CHANNELS.get, torrent_only=False)
    assert [s['channel'] for s in found] == ['pasateatorrent', 'repelis28']


def test_a_different_tmdb_id_is_another_title_even_with_the_same_name():
    files = [_movie('repelis28', tmdb='42')]
    assert bal.sources(files, 1215185, 'La infiltrada', 2024, CHANNELS.get, torrent_only=False) == []


def test_series_results_are_folders_with_balandros_name():
    serie = {'file': _url({'channel': 'cuevana3pro', 'action': 'temporadas', 'contentType': 'tvshow',
                           'contentSerieName': 'Tierra de Mafia', 'infoLabels': {'tmdb_id': '247718', 'year': 2025}}),
             'filetype': 'directory'}
    found = bal.sources([serie], '247718', 'Tierra de mafiosos', 2025, CHANNELS.get, torrent_only=False)
    assert found[0]['folder'] is True and found[0]['channel'] == 'cuevana3pro'
    assert found[0]['other'] == 'Tierra de Mafia'


def test_another_page_with_the_same_id_goes_after_and_says_its_name():
    files = [_movie('pasateatorrent', title='Infiltrada'), _movie('pasateatorrent'), _movie('repelis28')]
    found = bal.sources(files, 1215185, 'La infiltrada', 2024, CHANNELS.get, torrent_only=False)
    assert [(s['channel'], s['other']) for s in found] == [('pasateatorrent', ''), ('pasateatorrent', 'Infiltrada'),
                                                          ('repelis28', '')]


def test_the_same_link_twice_is_listed_once():
    files = [_movie('repelis28'), _movie('repelis28')]
    assert len(bal.sources(files, 1215185, 'La infiltrada', 2024, CHANNELS.get, torrent_only=False)) == 1


def test_channel_info_from_balandros_channel_file():
    text = json.dumps({'id': 'pasateatorrent', 'name': 'PasateATorrent', 'categories': ['torrent', 'movie'],
                       'language': ['cast']})
    assert bal.channel_info(text) == {'name': 'PasateATorrent', 'torrent': True, 'cast': True}
    assert bal.channel_info(json.dumps({'name': 'X', 'categories': ['movie'], 'language': ['lat']})) == \
        {'name': 'X', 'torrent': False, 'cast': False}
    assert bal.channel_info('') is None and bal.channel_info('no es json') is None


def test_found_sources_are_kept_for_a_while():
    assert bal.fresh({'time': 1000, 'sources': [{}]}, 1000 + bal.MAX_AGE - 1)
    assert not bal.fresh({'time': 1000, 'sources': [{}]}, 1000 + bal.MAX_AGE + 1)
    assert not bal.fresh(None, 0) and not bal.fresh({'time': 1000}, 1000)


def test_failed_is_the_last_source_that_did_not_start_lately():
    last = {'fuente': 'a', 'time': 990, 'ok': False}
    assert bal.failed(last, 'a', 1000) and not bal.failed(last, 'b', 1000)
    assert not bal.failed(dict(last, ok=True), 'a', 1000) and not bal.failed(None, 'a', 1000)
    assert not bal.failed(last, 'a', 990 + bal.RETRY)


def test_pick_skips_the_source_that_just_failed():
    paths = ['a', 'b', 'c']
    assert bal.pick(paths, None, 1000) == 'a'
    assert bal.pick(paths, {'fuente': 'a', 'time': 990, 'ok': True}, 1000) == 'a'
    assert bal.pick(paths, {'fuente': 'a', 'time': 990, 'ok': False}, 1000) == 'b'
    assert bal.pick(paths, {'fuente': 'c', 'time': 990, 'ok': False}, 1000) == 'a'
    assert bal.pick(paths, {'fuente': 'a', 'time': 1000 - bal.RETRY, 'ok': False}, 1000) == 'a'
    assert bal.pick(paths, {'fuente': 'z', 'time': 990, 'ok': False}, 1000) == 'a'
    assert bal.pick([], None, 0) is None


def _row(data, label='x', art=None):
    return {'label': label, 'path': _url(data), 'folder': False, 'art': art or {'thumb': 'p.jpg', 'fanart': 'f.jpg'},
            'info': {'plot': 'P', 'year': 2024}, 'uniqueids': {}, 'properties': {}}


def test_recent_movies_play_straight_from_their_page():
    data = {'channel': 'pasateatorrent', 'action': 'findvideos', 'contentTitle': 'Gigante',
            'infoLabels': {'tmdb_id': '123', 'year': 2025}}
    item = bal.row_item(_row(data, 'Gigante [COLOR gray](2025)[/COLOR]'), 'peliculas')
    q = parse.parse_qs(item['path'].split('?', 1)[1])
    assert q['play'] == ['peliculas'] and q['tmdb'] == ['123'] and q['titulo'] == ['Gigante'] and q['anio'] == ['2025']
    assert q['fuente'] == [_url(data)]
    assert item['label'] == 'Gigante' and item['folder'] is False and item['properties'] == {'IsPlayable': 'true'}
    assert item['art'] == {'thumb': 'p.jpg', 'poster': 'p.jpg', 'fanart': 'f.jpg'}
    assert item['info'] == {'plot': 'P', 'year': 2024, 'title': 'Gigante', 'mediatype': 'movie'}
    assert item['uniqueids'] == {'tmdb': '123'}


def test_recent_series_open_their_seasons_once_each():
    t2 = {'channel': 'pasateatorrent', 'action': 'episodios', 'contentSerieName': 'Reacher',
          'infoLabels': {'tmdb_id': '108978', 'year': '-'}}
    rows = bal.row_items([_row(t2, 'Reacher Temp. 3'), _row(dict(t2, url='otra')), {'label': 'Siguientes ...',
                          'path': _url({'action': 'list_all'})}], 'series')
    assert len(rows) == 1 and rows[0]['folder'] is True and rows[0]['label'] == 'Reacher'
    assert rows[0]['path'] == 'plugin://script.papa.inicio/?serie=108978&titulo=Reacher'
    assert rows[0]['info']['mediatype'] == 'tvshow'


def test_each_palantir_row_has_its_balandro_list():
    assert set(bal.FILAS) == {'peliculas.estrenos', 'peliculas.recientes', 'peliculas.generos', 'series.novedades',
                              'series.nuevas', 'series.generos'}
    assert bal.decode(bal.row_url('peliculas.recientes'))['url'] == 'https://pasateatorrent.org/peliculas/'
    assert bal.decode(bal.row_url('series.novedades'))['url'] == 'https://dontorrent.shopping/series/hd/page/1'
    assert bal.decode(bal.row_url('series.generos')) == {'channel': 'seriespapayato', 'action': 'generos',
                                                         'search_type': 'tvshow'}


def _movie_row(tmdb, title, premiered):
    item = _row({'channel': 'pasateatorrent', 'action': 'findvideos', 'contentTitle': title,
                 'infoLabels': {'tmdb_id': tmdb}}, title)
    item['info'] = {'premiered': premiered} if premiered else {}
    return item


def test_estrenos_are_sorted_by_release_and_recent_keep_the_webs_order():
    items = [_movie_row('1', 'Vieja', '2019-03-01'), _movie_row('2', 'Nueva', '2025-11-01'),
             _movie_row('3', 'Sin fecha', None), _movie_row('4', 'Media', '2024-06-01')]
    assert [i['label'] for i in bal.fila('peliculas.estrenos', items)] == ['Nueva', 'Media', 'Vieja', 'Sin fecha']
    assert [i['label'] for i in bal.fila('peliculas.recientes', items)] == ['Vieja', 'Nueva', 'Sin fecha', 'Media']


def test_genres_row_opens_each_genre_in_the_assistant():
    genre = {'label': '[COLOR deepskyblue]Ciencia ficción[/COLOR]', 'art': {'thumb': 'g.png'},
             'path': _url({'channel': 'pasateatorrent', 'action': 'list_all',
                           'url': 'https://pasateatorrent.org/categoria/ciencia-ficcion/'})}
    other = {'label': 'Buscar', 'path': _url({'action': 'search'})}
    rows = bal.fila('peliculas.generos', [genre, other])
    assert len(rows) == 1 and rows[0]['label'] == 'Ciencia ficción' and rows[0]['folder'] is True
    q = parse.parse_qs(rows[0]['path'].split('?', 1)[1])
    assert q['genero'] == ['peliculas'] and q['fuente'] == [genre['path']] and rows[0]['art'] == {'thumb': 'g.png'}


def test_series_genres_only_in_spanish():
    def genre(label):
        return {'label': label, 'path': _url({'channel': 'seriespapayato', 'action': 'list_all', 'url': label})}
    labels = ['Acción', 'Action', 'Action & Adventure', 'Comedia', 'Comedia (s)', 'Sci-Fi & Fantasy', 'Thriller',
              'Reality', 'Western', 'War & Politics', 'Guerra']
    assert [r['label'] for r in bal.fila('series.generos', [genre(x) for x in labels])] == [
        'Acción', 'Comedia', 'Reality', 'Western', 'Guerra']


def test_row_pages_and_next_page():
    assert bal.row_kind(bal.row_url('peliculas.estrenos')) == 'peliculas'
    assert bal.row_kind(bal.row_url('series.nuevas')) == 'series'
    assert bal.row_kind(bal.row_url('peliculas.generos')) is None and bal.row_kind('plugin://x/') is None
    nxt = {'file': _url({'action': 'list_all', 'page': 2}), 'label': '[COLOR coral]Siguientes ...[/COLOR]'}
    files = [{'file': _url({'action': 'findvideos'}), 'label': 'Tony'}, nxt]
    assert bal.next_page(files) == nxt['file'] and bal.is_next(nxt) and not bal.is_next(files[0])
    assert bal.next_page(files[:1]) == ''


def test_series_rows_come_from_dontorrent_hd_and_it_says_its_quality():
    assert bal.decode(bal.row_url('series.novedades'))['channel'] == 'dontorrents'
    assert bal.row_kind(bal.row_url('series.nuevas')) == 'series'
    hd = {'label': 'Percy Jackson - 3ª Temporada [1080p]',
          'path': _url({'channel': 'dontorrents', 'url': 'https://d/serie/1/1/Percy-Jackson-3-Temporada-1080p'})}
    sd = {'label': 'Anestesia - 1ª Temporada [720p]',
          'path': _url({'channel': 'dontorrents', 'url': 'https://d/serie/2/2/Anestesia-1-Temporada-720p'})}
    assert bal.says_hd(hd) and not bal.says_hd(sd)
    assert bal.needs_page('https://pasateatorrent.org/tony/') and not bal.needs_page('https://d/serie/1/1/x-1080p')


def test_estrenos_only_this_year():
    def item(year):
        return {'label': str(year), 'info': {'year': year} if year else {}}
    many = [item(2026)] * 10 + [item(2025), item(2012), item(None)]
    assert {i['label'] for i in bal.this_year(many, 2026)} == {'2026'}
    few = [item(2027), item(2026), item(2012)]  # enero: aún hay pocas del año
    assert [i['label'] for i in bal.this_year(few, 2027)] == ['2027', '2026']
    assert bal.year_of({'info': {'premiered': '2026-03-01'}}) == 2026
