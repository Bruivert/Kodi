from urllib import parse

from resources.lib import fichas


def test_play_and_serie_urls_are_the_assistants():
    url = fichas.play_url('peliculas', 1215185, 'La infiltrada', '2024', fuente='plugin://x/?y=1&z=2')
    assert url.startswith('plugin://script.papa.inicio/?play=peliculas&tmdb=1215185&titulo=La+infiltrada&anio=2024')
    assert parse.parse_qs(url.split('?', 1)[1])['fuente'] == ['plugin://x/?y=1&z=2']
    ep = parse.parse_qs(fichas.play_url('series', 1, 'X', season=2, episode=5).split('?', 1)[1])
    assert ep['t'] == ['2'] and ep['e'] == ['5'] and 'anio' not in ep
    assert fichas.serie_url(247718, 'Tierra de mafiosos', '2025') == \
        'plugin://script.papa.inicio/?serie=247718&titulo=Tierra+de+mafiosos&anio=2025'


def _item(mediatype, **kw):
    item = {'label': 'X', 'path': 'plugin://plugin.video.palantir3/?abc', 'folder': mediatype != 'movie', 'art': {},
            'info': {'title': 'Gigante', 'year': 2025, 'mediatype': mediatype}, 'uniqueids': {'tmdb': '7'},
            'properties': {'IsPlayable': 'true'} if mediatype == 'movie' else {}}
    item.update(kw)
    return item


def test_palantir_rows_play_through_the_assistant():
    movie = fichas.from_palantir(_item('movie'))
    assert movie['path'] == 'plugin://script.papa.inicio/?play=peliculas&tmdb=7&titulo=Gigante&anio=2025'
    assert movie['folder'] is False and movie['properties'] == {'IsPlayable': 'true'}
    show = fichas.from_palantir(_item('tvshow', properties={'IsPlayable': 'false'}))
    assert show['path'] == 'plugin://script.papa.inicio/?serie=7&titulo=Gigante&anio=2025'
    assert show['folder'] is True and show['properties'] == {}


def test_what_is_not_a_title_stays_as_it_was():
    genre = _item('video')
    assert fichas.from_palantir(genre) is genre
    no_id = _item('movie', uniqueids={})
    assert fichas.from_palantir(no_id) is no_id
