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


# Títulos reales en YouTube de los tráileres que eligió TMDb como es-ES en la caja (17/11/2026).
SPANISH_TITLES = [
    'La bola negra: Tráiler oficial | Movistar Plus',
    'VERITY. LA SOMBRA DE UN ENGAÑO | Téaser Tráiler Oficial en español. 2 de octubre en cines.',
    'En el corazón de la bestia | Tráiler Oficial | Paramount Pictures Spain',
    'Prácticamente magia 2 | Tráiler Oficial',
    'LA MANGOSTA Tráiler Español Oficial (2026) Liam Neeson, Acción',
    'Puño de león - Tráiler español',
    'Resident Evil | Nuevo Tráiler Oficial en español HD. En cines 18 de septiembre.',
    'Matchbox: la película — Tráiler oficial | Apple TV',
]
# Para "Enfrentados: Marfil", TMDb da como es-ES este teaser inglés.
MARFIL = 'Drawn Together - Official Teaser | Prime Video Canada'


def test_looks_english_only_for_english_or_subtitled_titles():
    assert not any(t.looks_english(x) for x in SPANISH_TITLES)
    assert t.looks_english(MARFIL)
    assert t.looks_english('Tráiler oficial subtitulado')  # se oye el original, en inglés
    assert t.looks_english('Matchbox - Tráiler VOSE')
    assert not t.looks_english('Official Trailer (Español)')  # mezcla, pero dice que es en español
    assert not t.looks_english('')
    assert not t.looks_english(None)


class FakeWeb:
    """TMDb por ruta y YouTube (oEmbed) por clave de vídeo."""

    def __init__(self, routes, titles):
        self.routes, self.titles, self.calls = routes, titles, []

    def __call__(self, url):
        self.calls.append(url)
        parsed = urlparse(url)
        if parsed.path == '/oembed':
            key = parse_qs(parsed.query)['url'][0].rsplit('v=', 1)[-1]
            if key not in self.titles:
                raise IOError('404 oembed ' + key)
            return {'title': self.titles[key], 'author_name': 'canal'}
        if parsed.path not in self.routes:
            raise IOError('404 ' + parsed.path)
        return self.routes[parsed.path]


def test_english_trailer_mislabelled_as_spain_spanish_is_skipped():
    vids = [video('lc7LU9fhgG0', size=2160), video('bueno', size=1080)]
    web = FakeWeb({'/3/movie/1440098/videos': {'results': vids}},
                  {'lc7LU9fhgG0': MARFIL, 'bueno': 'Enfrentados: Marfil | Tráiler oficial'})
    assert t.spain_trailer('movie', 1440098, 'K', web) == 'bueno'


def test_only_english_candidates_give_nothing():
    web = FakeWeb({'/3/movie/1440098/videos': {'results': [video('lc7LU9fhgG0')]}}, {'lc7LU9fhgG0': MARFIL})
    assert t.spain_trailer('movie', 1440098, 'K', web) is None


def test_subtitled_name_in_tmdb_is_skipped_without_asking_youtube():
    vids = [dict(video('vose', size=2160), name='Tráiler subtitulado'), dict(video('dob'), name='Tráiler doblado')]
    web = FakeWeb({'/3/movie/7/videos': {'results': vids}}, {'dob': 'Peli | Tráiler oficial'})
    assert t.spain_trailer('movie', 7, 'K', web) == 'dob'
    assert not [c for c in web.calls if 'vose' in c]


def test_unverifiable_youtube_title_keeps_tmdb_choice():
    web = FakeWeb({'/3/movie/7/videos': {'results': [video('es1')]}}, {})  # YouTube no contesta
    assert t.spain_trailer('movie', 7, 'K', web) == 'es1'


def test_oembed_url_asks_youtube_for_the_video():
    q = parse_qs(urlparse(t.oembed_url('abc')).query)
    assert urlparse(t.oembed_url('abc')).netloc == 'www.youtube.com'
    assert q['url'] == ['https://www.youtube.com/watch?v=abc'] and q['format'] == ['json']
