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


# --- Índice y búsqueda sobre una base con la forma de la de Palantir ---
import os
import sqlite3

import pytest

COLS = 'tmdb INTEGER, titulo TEXT, plot TEXT, poster TEXT, fondo TEXT, categoria TEXT, genero TEXT, mpaa TEXT, ' \
       'fecha TEXT, trailer TEXT, clearlogo TEXT, rating TEXT'


@pytest.fixture
def palantir_db(tmp_path):
    path = str(tmp_path / 'settings.xml')  # así se llama en la caja
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE pelis (%s, duration INTEGER)' % COLS)
    con.execute('CREATE TABLE series (%s)' % COLS)
    con.execute('CREATE TABLE enlaces_pelis (tmdb INTEGER, link TEXT)')
    con.execute('CREATE TABLE enlaces_series (tmdb INTEGER, link TEXT)')
    pelis = [(1, 'La ballena', 'Película', True), (2, 'Una ballena', 'Película', True),
             (3, 'Ballena sin enlace', 'Película', False), (4, 'Ballena animada', 'Dibujo', True),
             (5, "Señor O'Brien", 'Película', True)]
    pelis += [(100 + i, 'Ballena %03d' % (i + 1), 'Película', True) for i in range(70)]
    for tmdb, titulo, categoria, enlace in pelis:
        con.execute('INSERT INTO pelis (tmdb, titulo, categoria, poster, rating, duration) VALUES (?,?,?,?,?,?)',
                    (tmdb, titulo, categoria, '/p%d.jpg' % tmdb, '7.0/6.0', 5400))
        if enlace:
            con.execute('INSERT INTO enlaces_pelis VALUES (?, ?)', (tmdb, 'x'))
    for tmdb, titulo, categoria in ((10, 'The Pitt', 'General'), (11, 'Pitt novela', 'Novela')):
        con.execute('INSERT INTO series (tmdb, titulo, categoria) VALUES (?,?,?)', (tmdb, titulo, categoria))
        con.execute('INSERT INTO enlaces_series VALUES (?, ?)', (tmdb, 'x'))
    con.commit()
    con.close()
    return path


def test_search_finds_what_palantir_finds(palantir_db, tmp_path):
    idx = str(tmp_path / 'catalogo.db')
    pelis = cat.find(palantir_db, idx, 'peliculas', 'ballena')
    titles = [i['label'] for i in pelis]
    assert 'Ballena sin enlace' not in titles and 'Ballena animada' not in titles  # como sus vistas
    assert len(pelis) == cat.LIMIT  # 72 coinciden, 60 salen
    assert titles[0].startswith('Ballena 0') and 'La ballena' not in titles[:50]  # primero los que empiezan
    assert pelis[0]['art']['poster'].endswith('/p100.jpg') and pelis[0]['info']['duration'] == 5400
    assert [i['label'] for i in cat.find(palantir_db, idx, 'series', 'pitt')] == ['The Pitt']


def test_quotes_accents_and_wildcards_are_safe(palantir_db, tmp_path):
    idx = str(tmp_path / 'catalogo.db')
    assert [i['label'] for i in cat.find(palantir_db, idx, 'peliculas', "señor o'brien")] == ["Señor O'Brien"]
    assert cat.find(palantir_db, idx, 'peliculas', '100%_') == []


def test_short_or_empty_text_returns_nothing(palantir_db, tmp_path):
    idx = str(tmp_path / 'catalogo.db')
    for text in ('', '  ', '¿?', 'a'):
        assert cat.find(palantir_db, idx, 'peliculas', text) == []
    assert cat.find(None, idx, 'peliculas', 'ballena') == []  # Palantir sin instalar o sin base
    assert cat.find(palantir_db, idx, 'otra', 'ballena') == []
    assert cat.find(str(tmp_path / 'rota.db'), idx, 'peliculas', 'ballena') == []


def test_index_is_rebuilt_when_palantir_changes_and_replaced_at_once(palantir_db, tmp_path, monkeypatch):
    idx = str(tmp_path / 'catalogo.db')
    cat.find(palantir_db, idx, 'series', 'pitt')
    assert cat.index_current(idx, cat.stamp(palantir_db))
    assert not cat.index_current(idx, 'otro-sello') and not cat.index_current(str(tmp_path / 'no'), 'x')
    replaced = []
    real = os.replace
    monkeypatch.setattr(cat.os, 'replace', lambda a, b: (replaced.append((a, b)), real(a, b)))
    cat.build_index(palantir_db, idx, 'nuevo')
    assert replaced and replaced[0][1] == idx and replaced[0][0].endswith('.tmp')
    assert cat.index_current(idx, 'nuevo')
    assert not [p for p in os.listdir(str(tmp_path)) if p.endswith('.tmp')]


def test_palantir_db_is_only_read(palantir_db, tmp_path):
    before = open(palantir_db, 'rb').read()
    cat.find(palantir_db, str(tmp_path / 'catalogo.db'), 'peliculas', 'ballena')
    assert open(palantir_db, 'rb').read() == before
