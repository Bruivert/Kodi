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
        langs = parse_qs(parsed.query).get('include_video_language', [''])[0]
        if (parsed.path, langs) in self.routes:  # los vídeos en otros idiomas, aparte de los en español
            return self.routes[(parsed.path, langs)]
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


# --- Si TMDb no tiene un tráiler bueno: búsqueda en YouTube y, si tampoco, el teaser de TMDb ---

def yt_answer(*videos):
    """Respuesta de la búsqueda de YouTube (youtubei/v1/search), con la forma real pero solo lo que se usa."""
    items = [{'videoRenderer': {'videoId': key, 'title': {'runs': [{'text': title}]},
                                'ownerText': {'runs': [{'text': channel}]}, 'lengthText': {'simpleText': length}}}
             for key, title, channel, length in videos]
    items.insert(1, {'adSlotRenderer': {'title': 'anuncio'}})
    return {'contents': {'twoColumnSearchResultsRenderer': {'primaryContents': {'sectionListRenderer': {
        'contents': [{'itemSectionRenderer': {'contents': items}}]}}}}}


class FakePost:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, url, payload):
        self.calls.append((url, payload))
        if self.answer is None:
            raise IOError('sin red')
        return self.answer


# Lo que contesta YouTube a "Enfrentados: Marfil 2026 tráiler español" (17/11/2026, resumido).
MARFIL_SEARCH = [
    ('MXslFvkKD2s', 'ENFRENTADOS MARFIL Tráiler Oficial Español (2026)', 'Trailers In Spanish', '1:29'),
    ('sm3ADCASJwM', 'Enfrentados: Marfil Trailer | Prime Video', 'Amazon Prime Video España', '1:09'),
    ('djLAS5I0fqQ', 'Enfrentados: Marfil - Tráiler Oficial | Prime Video', 'Prime Video México', '1:10'),
    ('zXFHgkIINQw', 'ENFRENTADOS 2006 Trailer Español HD', 'TOP 5 FILMS', '1:53'),
]
MARFIL_TEASER = 'Teaser de Enfrentados: Marfil | Prime Video España'


def found(title, channel='Canal', length='1:30'):
    return {'key': 'k', 'title': title, 'channel': channel, 'seconds': t.seconds(length)}


def test_seconds_from_youtube_length():
    assert t.seconds('1:09') == 69
    assert t.seconds('1:02:03') == 3723
    assert t.seconds(None) is None
    assert t.seconds('EN DIRECTO') is None


def test_search_results_reads_the_videos_in_order():
    assert t.search_results(yt_answer(*MARFIL_SEARCH[:2])) == [
        {'key': 'MXslFvkKD2s', 'title': 'ENFRENTADOS MARFIL Tráiler Oficial Español (2026)',
         'channel': 'Trailers In Spanish', 'seconds': 89},
        {'key': 'sm3ADCASJwM', 'title': 'Enfrentados: Marfil Trailer | Prime Video',
         'channel': 'Amazon Prime Video España', 'seconds': 69}]
    assert t.search_results({}) == [] and t.search_results(None) == []


def test_search_result_must_be_this_film_dubbed_in_spain():
    def ok(video):
        return t.good_search_result(video, 'movie', 'Enfrentados: Marfil', '2026')
    assert ok(found('Enfrentados: Marfil Trailer | Prime Video', 'Amazon Prime Video España'))
    assert ok(found('ENFRENTADOS MARFIL Tráiler Oficial Español (2026)', 'Trailers In Spanish'))
    assert ok(found('📺 ENFRENTADOS: MARFIL | TRAILER ESPAÑOL | 9 Septiembre/26 - AMAZON PRIME', 'Trailer Ñ'))
    assert ok(found('Enfrentados: Marfil | Téaser en español (2025)'))  # el año de antes del estreno vale
    assert not ok(found('ENFRENTADOS 2006 Trailer Español HD'))  # otra película
    assert not ok(found('Enfrentados: Marfil Tráiler Español (2019)'))  # otro año
    assert not ok(found('ENFRENTADOS MARFIL Tráiler Español Latino (2026)'))  # doblaje latino
    assert not ok(found('Enfrentados: Marfil - Tráiler Oficial | Prime Video', 'Prime Video México'))
    assert not ok(found('Enfrentados: Marfil | Official Trailer', 'Prime Video España'))  # en inglés
    assert not ok(found('Enfrentados: Marfil Tráiler (2026) SUBTITULADO'))
    assert not ok(found('Enfrentados: Marfil (2026) Película completa en español', length='1:35:10'))
    assert not ok(found('Enfrentados: Marfil Tráiler Español', length=None))  # en directo o sin duración
    assert not ok(found('Enfrentados: Marfil | Reacción en español'))  # no es un tráiler
    assert not ok(found('Enfrentados: Marfil Trailer', 'Movie Clips'))  # nada dice que sea en español


def test_search_result_words_of_the_title_itself_do_not_count():
    assert t.good_search_result(found('1917 - Tráiler español'), 'movie', '1917', '2019')
    assert t.good_search_result(found('Narcos: México | Tráiler en español', 'Netflix España'), 'tv',
                                'Narcos: México', '2018')


def test_search_result_of_a_different_work_with_a_similar_title_is_rejected():
    # Visto con datos reales: el programa coreano "Running Man" y la serie "Bob Esponja" cogían tráileres de películas.
    assert not t.good_search_result(found('The Running Man I Tráiler Oficial I Paramount Pictures Spain',
                                          'Paramount Pictures Spain'), 'tv', 'Running Man', '2010')
    assert not t.good_search_result(found('BOB ESPONJA: UN HÉROE FUERA DEL AGUA | Teaser Tráiler Oficial | ESPAÑA',
                                          'Paramount'), 'tv', 'Bob Esponja', '1999')
    assert not t.good_search_result(found('Enfrentados: Marfil Trailer | Prime Video', 'Amazon Prime Video España'),
                                    'movie', 'Enfrentados', '2026')


def test_series_trailers_may_carry_any_season_year():
    season = found('Tulsa King | Tráiler Temporada 4 (TRÁILER EN ESPAÑOL) | Estreno: 22/10/2026 Skyshowtime',
                   'TopSeriesyPelículas')
    assert t.good_search_result(season, 'tv', 'Tulsa King', '2022')
    assert not t.good_search_result(found('Tulsa King Tráiler Oficial | Paramount+', 'Paramount+ México'),
                                    'tv', 'Tulsa King', '2022')


def test_youtube_trailer_prefers_spanish_channels():
    post = FakePost(yt_answer(*MARFIL_SEARCH))
    assert t.youtube_trailer('movie', 'Enfrentados: Marfil', '2026', post) == 'sm3ADCASJwM'
    url, payload = post.calls[0]
    assert urlparse(url).netloc == 'www.youtube.com' and urlparse(url).path == '/youtubei/v1/search'
    assert payload['query'] == 'Enfrentados: Marfil 2026 tráiler español'
    assert payload['context']['client']['hl'] == 'es' and payload['context']['client']['gl'] == 'ES'


def test_youtube_trailer_search_for_series_has_no_year():
    post = FakePost(yt_answer())
    assert t.youtube_trailer('tv', 'Tulsa King', '2022', post) is None
    assert post.calls[0][1]['query'] == 'Tulsa King serie tráiler español'


def test_youtube_trailer_gives_nothing_without_a_good_result_or_an_answer():
    other_film = yt_answer(('x', 'MI MEJOR ENEMIGA (2026) - Tráiler oficial español', 'AV FILMS', '2:24'))
    assert t.youtube_trailer('movie', 'Mi mejor amiga', '2026', FakePost(other_film)) is None
    assert t.youtube_trailer('movie', 'Mi mejor amiga', '2026', FakePost(None)) is None


def marfil_web(vids):
    return FakeWeb({'/3/movie/1440098/videos': {'results': vids},
                    '/3/movie/1440098': {'title': 'Enfrentados: Marfil', 'release_date': '2026-09-09'}},
                   {'lc7LU9fhgG0': MARFIL, 'tGWJVIXNcNI': MARFIL_TEASER})


def test_find_trailer_searches_youtube_when_tmdb_has_no_good_trailer():
    web = marfil_web([video('lc7LU9fhgG0'), video('tGWJVIXNcNI', vtype='Teaser')])
    assert t.find_trailer('movie', 1440098, 'K', web, FakePost(yt_answer(*MARFIL_SEARCH))) == 'sm3ADCASJwM'
    details = [urlparse(c) for c in web.calls if urlparse(c).path == '/3/movie/1440098'][0]
    assert parse_qs(details.query)['language'] == ['es-ES']


def test_find_trailer_falls_back_to_tmdb_spanish_teaser():
    web = marfil_web([video('lc7LU9fhgG0'), video('tGWJVIXNcNI', vtype='Teaser'),
                      video('mx', vtype='Teaser', country='MX')])
    assert t.find_trailer('movie', 1440098, 'K', web, FakePost(yt_answer())) == 'tGWJVIXNcNI'
    assert t.find_trailer('movie', 1440098, 'K', web, FakePost(None)) == 'tGWJVIXNcNI'


def test_find_trailer_does_not_search_when_tmdb_has_a_good_trailer():
    web = FakeWeb({'/3/movie/7/videos': {'results': [video('es1')]}}, {'es1': 'Peli | Tráiler oficial'})
    post = FakePost(yt_answer(*MARFIL_SEARCH))
    assert t.find_trailer('movie', 7, 'K', web, post) == 'es1'
    assert post.calls == []


def test_find_trailer_for_series_uses_name_and_first_air_date():
    web = FakeWeb({'/3/tv/9/videos': {'results': []}, '/3/tv/9': {'name': 'Tulsa King', 'first_air_date': '2022-11-13'}},
                  {})
    post = FakePost(yt_answer(('tk', 'Tulsa King | Tráiler Temporada 4 (TRÁILER EN ESPAÑOL)', 'TopSeriesyPelículas',
                               '1:49')))
    assert t.find_trailer('tv', 9, 'K', web, post) == 'tk'


def test_find_trailer_without_title_does_not_search():
    web = FakeWeb({'/3/movie/7/videos': {'results': []}}, {})  # TMDb no da los datos de la película
    post = FakePost(yt_answer(*MARFIL_SEARCH))
    assert t.find_trailer('movie', 7, 'K', web, post) is None
    assert post.calls == []


# --- Si no hay nada en castellano: como la web de TMDb, el vídeo en el idioma original ---

# Lo que tiene TMDb de "Ali G: Kién es yo?" (17/11/2026, resumido): todo en inglés.
ALI_G = [video('ANYUtxJ4Tzo', 'en', 'US', 'Teaser', published='2026-05-01T00:00:00.000Z'),
         video('6t7C4qaHihE', 'en', 'US', published='2026-07-01T00:00:00.000Z'),
         video('pV32AcPa-iA', 'en', 'US', published='2026-09-01T00:00:00.000Z'),
         video('288pl8AGwno', 'en', 'US', 'Featurette', published='2026-10-22T00:00:00.000Z')]


def original_web(kind, tid, info, original):
    return FakeWeb({'/3/%s/%s/videos' % (kind, tid): {'results': []}, '/3/%s/%s' % (kind, tid): info,
                    ('/3/%s/%s/videos' % (kind, tid), '%s,en,null' % info.get('original_language')):
                        {'results': original}}, {})


def test_original_trailers_prefer_trailer_then_teaser_then_clip_and_original_language():
    assert t.pick_original_trailer(ALI_G, 'en') == 'pV32AcPa-iA'  # el tráiler más nuevo, no el teaser
    assert t.pick_original_trailer([video('clip', 'de', 'DE', 'Clip')], 'de') == 'clip'
    assert t.pick_original_trailer([video('en', 'en', 'US'), video('de', 'de', 'DE')], 'de') == 'de'
    assert t.pick_original_trailer([video('t', 'de', 'DE', 'Teaser'), video('en', 'en', 'US')], 'de') == 'en'
    assert t.pick_original_trailer([video('f', 'en', 'US', 'Featurette'),
                                    video('v', 'en', 'US', site='Vimeo')], 'en') is None
    assert t.pick_original_trailer(None, 'en') is None


def test_original_videos_url_asks_original_language_and_english():
    query = parse_qs(urlparse(t.original_videos_url('movie', 5, 'de', 'K')).query)
    assert query['include_video_language'] == ['de,en,null']
    assert 'language' not in query


def test_find_trailer_without_spanish_gives_the_original_like_tmdb_web():
    web = original_web('movie', 1727734, {'title': 'Ali G: Kién es yo?', 'release_date': '2026-10-22',
                                          'original_language': 'en'}, ALI_G)
    assert t.find_trailer('movie', 1727734, 'K', web, FakePost(yt_answer())) == 'pV32AcPa-iA'
    # "El regalo de cumpleaños" (Das Geschenk): en TMDb solo hay un clip alemán de Netflix.
    web = original_web('movie', 1789549, {'title': 'El regalo de cumpleaños', 'release_date': '2026-10-30',
                                          'original_language': 'de'}, [video('LY4rm_99fvk', 'de', 'DE', 'Clip')])
    assert t.find_trailer('movie', 1789549, 'K', web, FakePost(None)) == 'LY4rm_99fvk'


def test_find_trailer_spanish_teaser_still_wins_over_the_original():
    web = original_web('movie', 1440098, {'title': 'Enfrentados: Marfil', 'release_date': '2026-09-09',
                                          'original_language': 'en'}, ALI_G)
    web.routes['/3/movie/1440098/videos'] = {'results': [video('tGWJVIXNcNI', vtype='Teaser')]}
    web.titles['tGWJVIXNcNI'] = MARFIL_TEASER
    assert t.find_trailer('movie', 1440098, 'K', web, FakePost(yt_answer())) == 'tGWJVIXNcNI'
