from urllib import parse

from resources.lib import lupa


def test_kinds_and_search_address():
    assert lupa.kinds('todo') == ['peliculas', 'series'] and lupa.kinds('series') == ['series']
    assert lupa.kinds('otra') == []
    url = lupa.search_url('series', 'La que', 'K')
    assert url.startswith('https://api.themoviedb.org/3/search/tv?')
    q = parse.parse_qs(url.split('?', 1)[1])
    assert q['query'] == ['La que'] and q['language'] == ['es-ES'] and q['api_key'] == ['K']


def test_movies_play_and_series_open_their_seasons():
    movie = {'id': 1215185, 'title': 'La infiltrada', 'release_date': '2024-10-11', 'poster_path': '/p.jpg',
             'backdrop_path': '/b.jpg', 'overview': 'ETA', 'vote_average': 7.1}
    item = lupa.to_items('peliculas', [movie, dict(movie, poster_path=None), {'title': 'sin id'}])
    assert len(item) == 1
    item = item[0]
    assert item['label'] == 'La infiltrada' and item['folder'] is False
    assert item['properties'] == {'IsPlayable': 'true'} and item['uniqueids'] == {'tmdb': '1215185'}
    assert item['path'] == 'plugin://script.papa.inicio/?play=peliculas&tmdb=1215185&titulo=La+infiltrada&anio=2024'
    assert item['art'] == {'poster': 'https://image.tmdb.org/t/p/w500/p.jpg',
                           'thumb': 'https://image.tmdb.org/t/p/w500/p.jpg',
                           'fanart': 'https://image.tmdb.org/t/p/w1280/b.jpg'}
    assert item['info'] == {'title': 'La infiltrada', 'mediatype': 'movie', 'plot': 'ETA', 'rating': 7.1,
                            'premiered': '2024-10-11', 'year': 2024}
    show = lupa.to_items('series', [{'id': 35338, 'name': 'La que se avecina', 'first_air_date': '',
                                     'poster_path': '/s.jpg'}])[0]
    assert show['folder'] is True and show['properties'] == {}
    assert show['path'] == 'plugin://script.papa.inicio/?serie=35338&titulo=La+que+se+avecina'
    assert show['info'] == {'title': 'La que se avecina', 'mediatype': 'tvshow'}


def test_limit():
    results = [{'id': n, 'title': str(n), 'poster_path': '/p'} for n in range(1, 40)]
    assert len(lupa.to_items('peliculas', results)) == lupa.LIMIT
