from resources.lib import catalogo as cat


def test_normalize_is_palantirs_map_string():
    assert cat.normalize('  La ballena ') == 'LA BALLENA'
    assert cat.normalize('Señor de los Anillos') == 'SENOR DE LOS ANILLOS'
    assert cat.normalize("Spider-Man: O'Brien ¿Qué?") == 'SPIDERMAN OBRIEN QUE'
    assert cat.normalize('Película 1917') == 'PELICULA 1917'
    assert cat.normalize('東京 ok') == 'OK'  # > U+00FF se quita; el espacio inicial que queda, también


def test_p3_url_round_trips_like_palantir():
    url = cat.p3_url({'tmdb': '1', 'action': 'selectvideos_', 'title': 'Ñ'})
    assert url.startswith('plugin://plugin.video.palantir3/?')
    assert cat.p3_decode(url.split('?', 1)[1]) == '{"action": \'selectvideos_\', "title": \'Ñ\', "tmdb": \'1\'}'


MOVIE = {'tmdb': 785084, 'titulo': 'La ballena', 'fecha': '2022-12-09', 'plot': 'P', 'poster': '/p.jpg',
         'fondo': '/f.jpg', 'duration': 7020, 'mpaa': '16', 'genero': 'Drama#Familia', 'trailer': 'Rhd5EyZ-rEs',
         'clearlogo': '/l.png', 'rating': '7.9/7.7'}


def _fields(item):
    return eval(cat.p3_decode(item['path'].split('?', 1)[1]))


def test_movie_item_plays_through_palantir():
    it = cat.to_item('peliculas', MOVIE)
    assert it['label'] == 'La ballena' and it['folder'] is False
    assert it['properties'] == {'IsPlayable': 'true'}
    assert it['art'] == {'poster': 'https://image.tmdb.org/t/p/w500/p.jpg',
                         'thumb': 'https://image.tmdb.org/t/p/w500/p.jpg',
                         'fanart': 'https://image.tmdb.org/t/p/w1280/f.jpg',
                         'clearlogo': 'https://image.tmdb.org/t/p/w500/l.png'}
    assert it['info'] == {'title': 'La ballena', 'year': 2022, 'premiered': '2022-12-09', 'plot': 'P', 'duration': 7020,
                          'mpaa': '16', 'genre': ['Drama', 'Familia'], 'rating': 7.9, 'mediatype': 'movie',
                          'trailer': 'plugin://plugin.video.youtube/play/?video_id=Rhd5EyZ-rEs'}
    assert it['uniqueids'] == {'tmdb': '785084'}
    fields = _fields(it)
    assert fields['action'] == 'selectvideos_' and fields['content'] == 'movies' and fields['tmdb'] == '785084'
    assert fields['isPlayable'] is True and fields['title'] == fields['label'] == 'La ballena'


def test_series_item_opens_palantirs_seasons():
    row = {k: v for k, v in MOVIE.items() if k != 'duration'}
    it = cat.to_item('series', dict(row, titulo='The Pitt'))
    fields = _fields(it)
    assert it['folder'] is True and it['properties'] == {} and it['info']['mediatype'] == 'tvshow'
    assert fields['action'] == 'listado_temporadaS' and fields['content'] == 'tvshows'
    assert fields['tvshowtitle'] == fields['label'] == 'The Pitt' and fields['page'] == 0


def test_incomplete_rows_still_make_an_item():
    bare = {'tmdb': 1, 'titulo': 'X', 'fecha': None, 'plot': None, 'poster': None, 'fondo': '', 'duration': None,
            'mpaa': None, 'genero': None, 'trailer': None, 'clearlogo': None, 'rating': '6.5'}
    it = cat.to_item('peliculas', bare)
    assert it['art'] == {} and it['info'] == {'title': 'X', 'rating': 6.5, 'mediatype': 'movie'}
    assert cat.to_item('peliculas', dict(bare, rating=''))['info'] == {'title': 'X', 'mediatype': 'movie'}
    assert None not in _fields(it).values()
