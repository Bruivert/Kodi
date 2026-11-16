from urllib.parse import parse_qs, urlparse

from resources.lib import trailers as t


def video(key, lang='es', country='ES', vtype='Trailer', site='YouTube', official=True, size=1080,
          published='2024-01-01T00:00:00.000Z'):
    return {'key': key, 'iso_639_1': lang, 'iso_3166_1': country, 'type': vtype, 'site': site,
            'official': official, 'size': size, 'published_at': published}


def test_spain_trailer_wins_over_mexican():
    vids = [video('mx', country='MX'), video('es')]
    assert t.pick_spain_trailer(vids) == 'es'


def test_only_latin_or_english_gives_nothing():
    vids = [video('mx', country='MX'), video('lat', country='419'), video('en', lang='en', country='US'),
            video('us', lang='en', country='ES')]
    assert t.pick_spain_trailer(vids) is None


def test_teasers_and_other_sites_are_ignored():
    vids = [video('teaser', vtype='Teaser'), video('vimeo', site='Vimeo')]
    assert t.pick_spain_trailer(vids) is None


def test_official_then_size_then_newest():
    vids = [video('fan', official=False, size=2160),
            video('old', size=1080, published='2023-01-01T00:00:00.000Z'),
            video('new', size=1080, published='2024-06-01T00:00:00.000Z'),
            video('small', size=720, published='2025-01-01T00:00:00.000Z')]
    assert t.pick_spain_trailer(vids) == 'new'


def test_empty_or_bad_input():
    assert t.pick_spain_trailer([]) is None
    assert t.pick_spain_trailer(None) is None


def test_videos_url_asks_spanish():
    q = parse_qs(urlparse(t.videos_url('movie', 603, 'KEY')).query)
    assert urlparse(t.videos_url('movie', 603, 'KEY')).path == '/3/movie/603/videos'
    assert q['language'] == ['es-ES'] and q['include_video_language'] == ['es'] and q['api_key'] == ['KEY']


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url):
        self.calls.append(url)
        path = urlparse(url).path
        if path not in self.routes:
            raise IOError('404 ' + path)
        return self.routes[path]


def test_resolve_uses_tmdb_id_when_present():
    http = FakeHttp({})
    assert t.resolve_tmdb_id('movie', '603', None, 'Matrix', '1999', 'K', http) == 603
    assert http.calls == []


def test_resolve_by_imdb_find():
    http = FakeHttp({'/3/find/tt0133093': {'movie_results': [{'id': 603}], 'tv_results': []}})
    assert t.resolve_tmdb_id('movie', '', 'tt0133093', '', '', 'K', http) == 603


def test_resolve_tv_by_search_with_year():
    http = FakeHttp({'/3/search/tv': {'results': [{'id': 1399}]}})
    assert t.resolve_tmdb_id('tv', '', '', 'Juego de tronos', '2011', 'K', http) == 1399
    q = parse_qs(urlparse(http.calls[0]).query)
    assert q['query'] == ['Juego de tronos'] and q['first_air_date_year'] == ['2011']


def test_resolve_returns_none_on_errors():
    assert t.resolve_tmdb_id('movie', '', 'tt1', '', '', 'K', FakeHttp({})) is None
    assert t.resolve_tmdb_id('movie', '', '', '', '', 'K', FakeHttp({})) is None


def test_spain_trailer_end_to_end_and_errors():
    http = FakeHttp({'/3/movie/603/videos': {'results': [video('mx', country='MX'), video('es1')]}})
    assert t.spain_trailer('movie', 603, 'K', http) == 'es1'
    assert t.spain_trailer('movie', 604, 'K', http) is None


def test_youtube_url():
    assert t.youtube_url('abc') == 'plugin://plugin.video.youtube/play/?video_id=abc'
