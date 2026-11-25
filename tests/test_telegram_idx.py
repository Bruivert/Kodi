from resources.lib import telegram_idx as ti


def _p(text):
    out = ti.parse(text)
    return out['title'], out['year'], out['season'], out['episode']


def test_movie_names():
    assert _p('Torrente.2.Mision.en.Marbella.(2001).1080p.BluRay.x264.mkv') == \
        ('Torrente 2 Mision en Marbella', 2001, None, None)
    assert _p('Amor Cruel (Cruel Love) (2026) ª[HD 1080P]  Castellano.mp4')[:2] == ('Amor Cruel (Cruel Love)', 2026)
    assert _p('Infielmente tuya (1984)[by Erpiyo].mkv') == ('Infielmente tuya', 1984, None, None)
    assert _p('El Templo Maldito.@CineNcasaa.mkv') == ('El Templo Maldito', None, None, None)
    assert _p('1917 (2019).mp4') == ('1917', 2019, None, None)


def test_episode_names():
    assert _p('@SeriesES - Reacher S04E02 1080p WEB-DL.mp4') == ('Reacher', None, 4, 2)
    assert _p('Los Serrano 1x02 [HDTV].avi') == ('Los Serrano', None, 1, 2)
    assert _p('Veronika 1 x 2') == ('Veronika', None, 1, 2)
    assert _p('Quién mató a Sara? T3 CAPITULO 3') == ('Quién mató a Sara?', None, 3, 3)
    assert _p('Dexter T4 C10 - Niños perdidos.mp4') == ('Dexter', None, 4, 10)
    assert _p('Águila Roja - T8 - Capítulo 96.mp4') == ('Águila Roja', None, 8, 96)
    assert _p('T-8/E-96')[2:] == (8, 96)
    assert _p('La que se avecina [Cap.1503] Castellano') == ('La que se avecina', None, 15, 3)
    assert _p('Los_misterios_de_Murdoch_9x07_Verano_del_75_H265,_1080p,_spanish.mkv')[:4] == \
        ('Los misterios de Murdoch', None, 9, 7)
    assert _p('Cap 7.mp4') == (None, None, None, 7)


def test_title_after_the_episode():
    out = ti.parse('1x06 - Snowpiercer [x265].mkv')
    assert (out['title'], out['season'], out['episode'], out['after']) == (None, 1, 6, 'Snowpiercer')


def test_describe_joins_name_and_message_text():
    v = {'name': 'Anillos 3x04 - Cine.mp4', 'caption': 'Los Anillos de Poder 3X04'}
    d = ti.describe(v)
    assert (d['title'], d['season'], d['episode'], d['alt']) == ('Anillos', 3, 4, 'Los Anillos de Poder')
    d = ti.describe({'name': None, 'caption': 'Quién mató a Sara? T3 CAPITULO 4'})
    assert (d['title'], d['season'], d['episode']) == ('Quién mató a Sara?', 3, 4)
    d = ti.describe({'name': '1x06 - Snowpiercer [x265].mkv', 'caption': ''})
    assert (d['title'], d['season'], d['episode']) == ('Snowpiercer', 1, 6)


def test_neighbours_give_the_series_name():
    videos = [{'id': 10, 'name': 'Doc Martin 10x06.mp4', 'caption': ''},
              {'id': 11, 'name': 'Cap 7.mp4', 'caption': ''},
              {'id': 12, 'name': 'Doc Martin 10x08.mp4', 'caption': ''},
              {'id': 50, 'name': 'Cap 1.mp4', 'caption': ''}]
    for v in videos:
        v['info'] = ti.describe(v)
    out = {v['id']: v['info'] for v in ti.fill_series(videos)}
    assert (out[11]['series'], out[11]['season'], out[11]['episode']) == ('Doc Martin', 10, 7)
    assert out[50]['series'] is None


def test_quality_is_only_a_label_for_telegram():
    assert ti.quality({'width': 1920, 'height': 800}) == '1080p'
    assert ti.quality({'width': 3840, 'height': 2160}) == '4K'
    assert ti.quality({'width': 1280, 'height': 720, 'name': 'x 1080p.mp4'}) == '720p'  # manda la resolución real
    assert ti.quality({'width': 480, 'height': 360}) == 'SD'
    assert ti.quality({'name': 'Outlander_S07E16_1080p_NF.mkv'}) == '1080p'
    assert ti.quality({'name': 'Serie [HDTV 720p][Cap.106].mkv'}) == '720p'
    assert ti.quality({'name': 'Split.[by Erpiyo].avi', 'size': 4e9}) == '?'


def test_language():
    assert ti.spanish({'name': 'Raqa (2024).mp4'})
    assert not ti.spanish({'name': 'We_Are_Young_2014_German_1080P.mp4'})
    assert not ti.spanish({'name': 'Magnum P.I. S04E12.mkv', 'caption': 'Català'})
    assert not ti.spanish({'name': 'Peli (2020) VOSE.mkv'})


def test_tmdb_matching():
    results = [{'id': 1, 'title': 'Godzilla', 'original_title': 'Godzilla', 'release_date': '1998-05-20'},
               {'id': 2, 'title': 'Godzilla', 'original_title': 'Godzilla', 'release_date': '2014-05-14'}]
    assert ti.match_movie('Godzilla', 2014, results)['id'] == 2
    assert ti.match_movie('Godzilla', None, results) is None  # dos iguales sin año: duda
    assert ti.match_movie('Godzila', 2015, results)['id'] == 2
    assert ti.match_movie('Otra cosa', 2014, results) is None
    shows = [{'id': 5, 'name': 'Doc Martin', 'original_name': 'Doc Martin', 'vote_count': 300},
             {'id': 6, 'name': 'Doctor Martín', 'original_name': 'Doctor Martín', 'vote_count': 10}]
    assert ti.match_show('Doc Martin', shows)['id'] == 5
    assert ti.match_show('Billions', shows) is None


def test_best_version_first():
    versions = [{'id': 1, 'quality': '4K', 'size': 9e9}, {'id': 2, 'quality': '1080p', 'size': 2e9},
                {'id': 3, 'quality': '1080p', 'size': 3e9}, {'id': 4, 'quality': 'SD', 'size': 1e9},
                {'id': 5, 'quality': '?', 'size': 4e9}, {'id': 6, 'quality': '720p', 'size': 5e9}]
    assert [v['id'] for v in sorted(versions, key=ti.rank)] == [3, 2, 1, 5, 6, 4]


def test_odd_years_and_double_titles():
    assert _p('Un lugar donde refugiarse ·2013·.mp4')[:2] == ('Un lugar donde refugiarse', 2013)
    assert _p('Los_juicios_de_Nuremberg_2023WEBDL_1080p_x264.mkv')[:2] == ('Los juicios de Nuremberg', 2023)
    assert _p('Gran_libertad_Sebastian_Meise,2021_Spanish_WEBDL.mkv')[1] == 2021
    assert _p('Ver La caída de la Casa Usher 1x01')[0] == 'La caída de la Casa Usher'
    assert ti.names('Amor Cruel (Cruel Love)') == ['Amor Cruel (Cruel Love)', 'Amor Cruel', 'Cruel Love']


def test_more_tmdb_matching():
    same = [{'id': 1, 'title': 'Crazy, Stupid, Love.', 'release_date': '2011-07-29', 'vote_count': 9000},
            {'id': 2, 'title': 'Crazy Stupid Love', 'release_date': '2019-01-01', 'vote_count': 3}]
    assert ti.match_movie('Crazy Stupid Love', None, same)['id'] == 1
    shows = [{'id': 7, 'name': 'El primer matrimonio de Georgie y Mandy', 'original_name': "Georgie & Mandy's First Marriage"}]
    assert ti.match_show('Georgie & Mandy', shows)['id'] == 7
    assert ti.match_show('Mandy', shows) is None


def test_generic_words_in_brackets_are_not_titles():
    assert ti.names('Dibujo de David (corto)') == ['Dibujo de David (corto)', 'Dibujo de David']


def test_topic_from_patched_addon_or_guessed():
    temas = {11: 'Películas', 22: 'Series'}
    assert ti.topic({'topic': 11, 'name': 'x 1x01.mp4'}, temas) == 'Películas'
    assert ti.topic({'topic': 22}, temas) == 'Series'
    assert ti.topic({'topic': 0, 'name': 'Hola.mp4'}, temas) is None  # otro tema (Chat, Peticiones…)
    assert ti.topic({'name': 'Reacher 4x02.mp4'}, temas) == 'Series'  # addon sin parche: se deduce
    assert ti.topic({'name': 'Tony (2026).mp4'}, temas) == 'Películas'
    v = ti.from_addon({'msg_id': 9, 'name': 'Tony (2026).mp4', 'text': '', 'w': 1920, 'h': 800, 'size': 5,
                       'duration': 60, 'topic': 11}, temas)
    assert v == {'id': 9, 'name': 'Tony (2026).mp4', 'caption': '', 'width': 1920, 'height': 800, 'size': 5,
                 'duration': 60, 'tema': 'Películas'}


def test_catalogue_and_store(tmp_path):
    import sqlite3

    def search(kind, query, year):
        if kind == 'movie' and query == 'Tony':
            return [{'id': 1, 'title': 'Tony', 'original_title': 'Tony', 'release_date': '2026-01-01'}]
        if kind == 'tv' and query == 'Reacher':
            return [{'id': 2, 'name': 'Reacher', 'original_name': 'Reacher', 'first_air_date': '2022-02-04'}]
        return []
    videos = [{'id': 10, 'name': 'Tony (2026).mp4', 'caption': '', 'tema': 'Películas', 'size': 1},
              {'id': 11, 'name': 'Reacher 4x02.mp4', 'caption': '', 'tema': 'Series', 'size': 2, 'width': 1920,
               'height': 1080},
              {'id': 12, 'name': 'Otra (1999) VOSE.mp4', 'caption': '', 'tema': 'Películas', 'size': 3},
              {'id': 13, 'name': 'Nada (2001).mp4', 'caption': '', 'tema': 'Películas', 'size': 4}]
    found = ti.catalogue(videos, search)
    assert found['pelis'] == [(1, 10, '?', 1)] and found['capitulos'] == [(2, 4, 2, 11, '1080p', 2)]
    assert list(found['sin_ficha']) == ['Nada (2001)']
    db = sqlite3.connect(str(tmp_path / 't.db'))
    ti.store(db, found, 13, -100, {11: 'Películas'})
    ti.store(db, found, 13, -100)  # repetir no duplica
    assert db.execute('SELECT COUNT(*) FROM pelis').fetchone()[0] == 1
    assert db.execute("SELECT titulo, año FROM titulos WHERE tipo = 'series'").fetchone() == ('Reacher', 2022)
    assert ti.last_msg(db) == 13 and ti.topics(db) == {11: 'Películas'}
