import base64
import json
from urllib import parse

from resources.lib import series as sr


def _f(item, label):
    url = 'plugin://plugin.video.balandro/?' + parse.quote(base64.b64encode(json.dumps(item).encode('utf-8')))
    return {'file': url, 'label': label}


def test_seasons_from_the_number_or_the_text():
    files = [_f({'action': 'episodios', 'contentType': 'season', 'contentSeason': 2}, '[COLOR tan]Temporada 02[/COLOR]'),
             _f({'action': 'episodios', 'contentType': 'season'}, '[COLOR tan]Temporada 01[/COLOR]'),
             _f({'action': 'episodios'}, 'Reacher [COLOR tan]Temp.[/COLOR] 3'),
             _f({'action': 'episodios'}, 'Sin número'),
             {'file': 'plugin://plugin.video.balandro/?action=', 'label': 'cabecera'}]
    listing = sr.parse_listing(files)
    assert [s['season'] for s in listing['seasons']] == [1, 2, 3]
    assert listing['seasons'][0]['path'] == files[1]['file'] and listing['episodes'] == [] and listing['next'] == ''


def test_episodes_even_with_balandros_typo_and_the_next_page():
    files = [_f({'action': 'findvideos', 'contentType': 'episode', 'ontentSeason': 1, 'contentEpisodeNumber': 2},
                '1x2 La que se avecina [COLOR tan]Temp.[/COLOR] 1 [COLOR goldenrod]Epis.[/COLOR] 2'),
             _f({'action': 'findvideos', 'contentSeason': 1, 'contentEpisodeNumber': '1'}, 'Piloto'),
             _f({'action': 'findvideos', 'contentSeason': 1, 'contentEpisodeNumber': '1'}, 'Piloto (otra versión)'),
             _f({'action': 'findvideos'}, 'Sin numeración'),
             _f({'action': 'episodios', 'page': 1}, '[COLOR coral]Siguientes ...[/COLOR]')]
    listing = sr.parse_listing(files)
    assert [(e['season'], e['episode']) for e in listing['episodes']] == [(1, 1), (1, 2)]
    assert listing['episodes'][1]['size'] == ''
    assert listing['episodes'][0]['path'] == files[1]['file']
    assert listing['next'] == files[4]['file'] and listing['seasons'] == []


def test_episodes_keep_their_size_and_skip_whole_season_torrents():
    files = [_f({'action': 'findvideos', 'contentSeason': 2, 'contentEpisodeNumber': 1, 'quality': '1.42GB'}, '2x1'),
             _f({'action': 'findvideos', 'contentSeason': 99, 'contentEpisodeNumber': 99, 'quality': '9GB'}, 'x')]
    assert sr.parse_listing(files)['episodes'] == [{'season': 2, 'episode': 1, 'path': files[0]['file'],
                                                    'size': '1.42GB'}]


def test_seasons_from_one_page_per_season():
    found = [{'label': 'Reacher [COLOR tan]Temp.[/COLOR] 3', 'path': 'P3'}, {'label': 'Reacher Temporada 1',
             'path': 'P1'}, {'label': 'Reacher Temporada 1', 'path': 'otra'}, {'label': 'Reacher', 'path': 'P'}]
    assert sr.seasons_from_sources(found) == [{'season': 1, 'path': 'P1', 'hd': False},
                                              {'season': 3, 'path': 'P3', 'hd': False}]


def test_dontorrent_seasons_only_in_1080p_or_4k():
    found = [{'channel': 'dontorrents', 'label': 'La playlist - 1ª Temporada', 'path': 'SD'},
             {'channel': 'dontorrents', 'label': 'La playlist - 1ª Temporada [720p]', 'path': '720'},
             {'channel': 'dontorrents', 'label': 'Percy Jackson - 3ª Temporada [1080p]', 'path': 'P3'},
             {'channel': 'dontorrents', 'label': 'Percy Jackson - 2ª Temporada', 'path': 'x',
              'url': 'https://d/serie/1/1/Percy-Jackson-2-Temporada-4K'}]
    assert sr.seasons_from_sources(found) == [{'season': 2, 'path': 'x', 'hd': True},
                                              {'season': 3, 'path': 'P3', 'hd': True}]
    balandro_names = [{'channel': 'dontorrents', 'path': 'P1',
                       'label': 'Percy - 1ª [COLOR tan]Temp.[/COLOR] [1080p] [COLOR gray](2023)[/COLOR]'},
                      {'channel': 'dontorrents', 'path': 'X', 'label': 'Percy - 2ª [COLOR tan]Temp.[/COLOR] [720p]'}]
    assert sr.seasons_from_sources(balandro_names) == [{'season': 1, 'path': 'P1', 'hd': True}]


def test_hd_seasons_say_so_in_their_address():
    items = sr.season_items(1, 'X', '', [{'season': 3, 'path': 'P3', 'hd': True}], None)
    assert parse.parse_qs(items[0]['path'].split('?', 1)[1])['hd'] == ['1']


def test_runtime_from_tmdb():
    season = {'episodes': [{'episode_number': 1, 'runtime': 62}, {'episode_number': 2, 'runtime': None}]}
    assert sr.runtime({'episode_run_time': [45]}, season, 1) == 62
    assert sr.runtime({'episode_run_time': [45]}, season, 2) == 45
    assert sr.runtime({}, {}, 1) is None


def test_find_episode():
    eps = [{'season': 1, 'episode': n, 'path': 'p%d' % n} for n in (1, 2, 3)] + [{'season': 2, 'episode': 1,
                                                                                   'path': 'q1'}]
    assert sr.find_episode(eps, 1, 2) == 'p2' and sr.find_episode(eps, 3, 1) is None


SHOW = {'poster_path': '/s.jpg', 'backdrop_path': '/b.jpg', 'overview': 'Serie',
        'seasons': [{'season_number': 1, 'poster_path': '/t1.jpg', 'overview': 'Primera'},
                    {'season_number': 2, 'poster_path': None}]}


def test_season_items_have_each_seasons_poster():
    items = sr.season_items(35338, 'La que se avecina', '2007', [{'season': 1, 'path': 'P1'},
                                                                  {'season': 2, 'path': 'P2'}], SHOW)
    assert [i['label'] for i in items] == ['Temporada 1', 'Temporada 2'] and all(i['folder'] for i in items)
    assert items[0]['art'] == {'poster': 'https://image.tmdb.org/t/p/w500/t1.jpg',
                               'thumb': 'https://image.tmdb.org/t/p/w500/t1.jpg',
                               'fanart': 'https://image.tmdb.org/t/p/w1280/b.jpg'}
    assert items[1]['art']['poster'].endswith('/s.jpg') and items[1]['info']['plot'] == 'Serie'
    q = parse.parse_qs(items[0]['path'].split('?', 1)[1])
    assert q == {'temporada': ['1'], 'tmdb': ['35338'], 'titulo': ['La que se avecina'], 'anio': ['2007'],
                 'fuente': ['P1']}
    assert sr.season_items(1, 'X', '', [{'season': 1, 'path': 'P'}], None)[0]['art'] == {}


def test_episode_items_play_with_tmdb_photo_and_names():
    season = {'episodes': [{'episode_number': 1, 'name': 'Un nuevo vecino', 'overview': 'R', 'still_path': '/e1.jpg',
                            'air_date': '2007-04-22', 'runtime': 80, 'vote_average': 7.5}]}
    items = sr.episode_items(35338, 'La que se avecina', '2007', [{'season': 1, 'episode': 1, 'path': 'E1'},
                                                                   {'season': 1, 'episode': 2, 'path': 'E2'}],
                             SHOW, {1: season})
    assert [i['label'] for i in items] == ['1. Un nuevo vecino', '2. Capítulo 2']
    assert items[0]['properties'] == {'IsPlayable': 'true'} and items[0]['folder'] is False
    assert items[0]['art']['thumb'] == 'https://image.tmdb.org/t/p/w780/e1.jpg'
    assert items[0]['info'] == {'title': 'Un nuevo vecino', 'tvshowtitle': 'La que se avecina', 'season': 1,
                                'episode': 1, 'mediatype': 'episode', 'plot': 'R', 'premiered': '2007-04-22',
                                'duration': 4800, 'rating': 7.5}
    q = parse.parse_qs(items[1]['path'].split('?', 1)[1])
    assert q['play'] == ['series'] and q['t'] == ['1'] and q['e'] == ['2'] and q['fuente'] == ['E2']
    assert items[1]['art']['thumb'].endswith('/s.jpg')


def test_tmdb_addresses_are_in_spanish():
    assert sr.show_url(1, 'K') == 'https://api.themoviedb.org/3/tv/1?api_key=K&language=es-ES'
    assert sr.season_url(1, 2, 'K') == 'https://api.themoviedb.org/3/tv/1/season/2?api_key=K&language=es-ES'


def test_seasons_and_episodes_already_aired_according_to_tmdb():
    show = {'seasons': [{'season_number': 0, 'episode_count': 3, 'air_date': '2020-01-01'},
                        {'season_number': 2, 'episode_count': 8, 'air_date': '2025-12-01'},
                        {'season_number': 1, 'episode_count': 8, 'air_date': '2022-02-04'},
                        {'season_number': 3, 'episode_count': 8, 'air_date': '2026-12-20'},
                        {'season_number': 4, 'episode_count': 0, 'air_date': None}]}
    assert sr.tmdb_seasons(show, '2026-11-23') == [{'season': 1, 'path': 'tmdb', 'hd': True},
                                                   {'season': 2, 'path': 'tmdb', 'hd': True}]
    season = {'episodes': [{'episode_number': 1, 'air_date': '2026-11-20'}, {'episode_number': 2, 'air_date': '2026-11-27'},
                           {'episode_number': 3}]}
    assert sr.tmdb_episodes(season, 3, '2026-11-23') == [{'season': 3, 'episode': 1, 'path': ''}]
    assert sr.tmdb_seasons(None, '2026-11-23') == [] and sr.tmdb_episodes(None, 1, 'x') == []
