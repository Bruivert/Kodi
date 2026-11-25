import sqlite3

from resources.lib import telegram as tg


def _db(tmp_path):
    path = str(tmp_path / 'telegram.db')
    db = sqlite3.connect(path)
    db.executescript('''
        CREATE TABLE pelis (tmdb INTEGER, msg INTEGER PRIMARY KEY, calidad TEXT, bytes INTEGER);
        CREATE TABLE capitulos (tmdb INTEGER, temporada INTEGER, capitulo INTEGER, msg INTEGER PRIMARY KEY,
                                calidad TEXT, bytes INTEGER);
        CREATE TABLE estado (clave TEXT PRIMARY KEY, valor TEXT);
        INSERT INTO estado VALUES ('grupo', '-1009999999999');
        INSERT INTO pelis VALUES (99, 10, 'SD', 500), (99, 11, '1080p', 2000), (99, 12, '4K', 9000), (7, 13, '?', 1);
        INSERT INTO capitulos VALUES (5, 1, 2, 20, '720p', 900), (5, 1, 2, 21, '1080p', 1200), (5, 1, 3, 22, '?', 1);
    ''')
    db.commit()
    db.close()
    return path


def test_addresses():
    b = tg.base('abc')
    assert b == 'http://127.0.0.1:8765/tabc'
    assert tg.stream_url(b, -1009999999999, 4242) == b + '/stream/-1009999999999/4242/video.mp4'
    assert tg.prefetch_url(b, -100, 5) == b + '/api/prefetch?chat=-100&msg=5'


def test_versions_best_first(tmp_path):
    path = _db(tmp_path)
    assert tg.peer(path) == -1009999999999
    assert [v['msg'] for v in tg.versions(path, 'peliculas', '99')] == [11, 12, 10]
    assert tg.versions(path, 'peliculas', 99)[0] == {'msg': 11, 'quality': '1080p', 'size': 2000}
    assert [v['msg'] for v in tg.versions(path, 'series', '5', 1, 2)] == [21, 20]
    assert tg.versions(path, 'series', '5', 2, 1) == []


def test_without_catalogue_nothing_breaks(tmp_path):
    assert tg.versions(str(tmp_path / 'no.db'), 'peliculas', '1') == []
    assert tg.peer(str(tmp_path / 'no.db')) is None
    assert tg.versions(_db(tmp_path), 'peliculas', '') == []


def test_newest_titles_for_the_rows(tmp_path):
    path = _db(tmp_path)
    db = sqlite3.connect(path)
    db.executescript('''
        CREATE TABLE titulos (tmdb INTEGER, tipo TEXT, titulo TEXT, año INTEGER, poster TEXT, fondo TEXT,
                              sinopsis TEXT, nota REAL);
        INSERT INTO titulos VALUES (99, 'peliculas', 'Vieja', 1955, '/p99.jpg', '/f99.jpg', 'x', 7.5),
                                   (7, 'peliculas', 'Nueva', 2026, '/p7.jpg', NULL, NULL, NULL),
                                   (5, 'series', 'Serie', 2024, '/p5.jpg', '/f5.jpg', 'y', 8.0);
    ''')
    db.commit()
    db.close()
    movies = tg.newest(path, 'peliculas')
    assert [m['title'] for m in movies] == ['Nueva', 'Vieja']  # mensaje 13 es más nuevo que el 12
    assert movies[1] == {'id': 99, 'title': 'Vieja', 'release_date': '1955-01-01', 'poster_path': '/p99.jpg',
                         'backdrop_path': '/f99.jpg', 'overview': 'x', 'vote_average': 7.5}
    assert tg.newest(path, 'series')[0]['name'] == 'Serie' and tg.newest(path, 'series', 0) == []
    assert [m['title'] for m in tg.newest(path, 'peliculas', since=2025)] == ['Nueva']
    assert tg.newest(str(tmp_path / 'no.db'), 'series') == []


def test_mix_alternates_without_repeating():
    row = [{'label': 'a', 'uniqueids': {'tmdb': '1'}}, {'label': 'b', 'uniqueids': {'tmdb': '2'}}]
    extra = [{'label': 'x', 'uniqueids': {'tmdb': '2'}}, {'label': 'y', 'uniqueids': {'tmdb': '3'}},
             {'label': 'z', 'uniqueids': {'tmdb': '4'}}]
    assert [i['label'] for i in tg.mix(row, extra)] == ['a', 'y', 'b', 'z']
    assert tg.mix([], extra)[0]['label'] == 'x'


def test_update_only_once_a_day_at_night():
    import time as _t
    night = _t.struct_time((2026, 11, 25, 4, 0, 0, 2, 329, -1))
    day = _t.struct_time((2026, 11, 25, 15, 0, 0, 2, 329, -1))
    assert tg.due(night, '2026-11-24') and not tg.due(night, '2026-11-25') and not tg.due(day, '')


def test_new_videos_stop_at_what_is_known():
    pages = {None: {'items': [{'msg_id': 30}, {'msg_id': 29}], 'next': 'c1'},
             'c1': {'items': [{'msg_id': 28}, {'msg_id': 20}], 'next': 'c2'},
             'c2': {'items': [{'msg_id': 19}], 'next': None}}
    asked = []

    def fetch(url):
        cursor = url.split('cursor=')[1] if 'cursor=' in url else None
        asked.append(cursor)
        return pages[cursor]
    got = tg.new_videos(fetch, 'http://x/t1', -100, since=20)
    assert [i['msg_id'] for i in got] == [30, 29, 28] and asked == [None, 'c1']
    assert 'chats=-100' in tg.media_url('http://x/t1', -100) and 'kind=all' in tg.media_url('http://x/t1', -100)


def test_split_movies_play_as_one(tmp_path):
    path = _db(tmp_path)
    db = sqlite3.connect(path)
    db.executescript("CREATE TABLE partes (msg INTEGER PRIMARY KEY, primera INTEGER, numero INTEGER);"
                     "INSERT INTO pelis VALUES (55, 30, '1080p', 1000);"
                     "INSERT INTO partes VALUES (30, 30, 1), (31, 30, 2);")
    db.commit()
    db.close()
    v = tg.versions(path, 'peliculas', '55')
    assert v == [{'msg': 30, 'quality': '1080p', 'size': 1000, 'parts': [30, 31]}]
    b = tg.base('k')
    assert tg.play_target(b, -100, v[0]) == 'stack://%s , %s' % (tg.stream_url(b, -100, 30), tg.stream_url(b, -100, 31))
    assert tg.play_target(b, -100, {'msg': 9}) == tg.stream_url(b, -100, 9)
    assert 'parts' not in tg.versions(path, 'peliculas', '99')[0]


def test_hd_in_the_group_means_no_waiting_for_pelis():
    assert tg.has_hd([{'quality': '720p'}, {'quality': '1080p'}]) and tg.has_hd([{'quality': '4K'}])
    assert not tg.has_hd([{'quality': '?'}, {'quality': 'SD'}]) and not tg.has_hd([])
