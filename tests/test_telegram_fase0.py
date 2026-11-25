from tools import telegram_fase0 as t0


def test_env_is_read_and_missing_values_are_named(tmp_path):
    env = tmp_path / 'telegram.env'
    env.write_text('# comentario\napi_id=123\napi_hash="abc"\ngrupo=\n', encoding='utf-8')
    values = t0.read_env(str(env))
    assert values == {'api_id': '123', 'api_hash': 'abc', 'grupo': ''}
    assert t0.missing(values) == ['grupo']


def test_resolution_by_width_and_height():
    assert t0.resolution(1920, 800) == '1080p'
    assert t0.resolution(3840, 1608) == '4K'
    assert t0.resolution(1280, 534) == '720p'
    assert t0.resolution(720, 404) == 'SD'
    assert t0.resolution(None, None) == 'desconocida'


def test_names_are_understood():
    assert t0.parse_name('Torrente.2.Mision.en.Marbella.(2001).1080p.BluRay.x264.mkv') == \
        {'title': 'Torrente 2 Mision en Marbella', 'year': 2001, 'season': None, 'episode': None}
    assert t0.parse_name('@SeriesES - Reacher S04E02 1080p WEB-DL.mp4') == \
        {'title': 'Reacher', 'year': None, 'season': 4, 'episode': 2}
    assert t0.parse_name('Los Serrano 1x02 [HDTV].avi')['season'] == 1
    assert t0.parse_name('La que se avecina [Cap.1503] Castellano')['episode'] == 3
    assert t0.parse_name('Tony (2026)\nUna película de…')['year'] == 2026
    assert t0.parse_name('')['title'] is None


def test_summary():
    videos = [{'name': 'Reacher S04E01.mkv', 'width': 1920, 'height': 1080, 'size': 2e9},
              {'name': 'Reacher S04E02.mkv', 'width': 1920, 'height': 1080, 'size': 2e9},
              {'caption': 'Tony (2026)', 'width': 1280, 'height': 720, 'size': 1e9},
              {'name': 'VID_001.mp4'}]
    report = t0.summarize(videos)
    assert report['videos'] == 4 and report['gb'] == 5.0
    assert report['calidades'] == {'1080p': 2, '720p': 1, 'desconocida': 1}
    assert report['capitulos'] == 2 and report['series'] == 1 and report['con_año'] == 1


def test_only_series_and_movie_topics():
    assert t0.wanted_topic('🎬 PELÍCULAS') and t0.wanted_topic('Series 📺') and t0.wanted_topic('Pelis')
    assert not t0.wanted_topic('General') and not t0.wanted_topic('Peticiones')
