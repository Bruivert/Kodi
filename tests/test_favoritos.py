from urllib.parse import parse_qs, urlparse

from resources.lib import favoritos as fv

# favourites.xml de la caja (17/11/2026), recortado.
XML = '''<favourites>
    <favourite name="[COLOR red][B]* [/B][/COLOR][COLOR ffffffff] The Hack[/COLOR] [COLOR ffc0c0c0](2025)[/COLOR] [COLOR ffc0c0c0][Esp, Eng][/COLOR]" thumb="https://image.tmdb.org/t/p/w500/hack.jpg">ActivateWindow(10025,&quot;plugin://plugin.video.palantir3/?abc&quot;,return)</favourite>
    <favourite name="[COLOR lightcyan]AGENDA [/COLOR][COLOR lightblue]STREAMTP[/COLOR]" thumb="http://addonbg.co/black/img/deportes.png">ActivateWindow(10025,"plugin://plugin.video.blackghost/?mode=17&amp;url=x",return)</favourite>
    <favourite name="[COLOR ffffffff] Father Mother Sister Brother[/COLOR] [COLOR ffc0c0c0](2025)[/COLOR] [COLOR ff008000][1080p][/COLOR]" thumb="https://image.tmdb.org/t/p/w500/fmsb.jpg">PlayMedia("plugin://plugin.video.palantir3/?def")</favourite>
    <favourite name="Add-ons de vídeo" thumb="DefaultAddonVideo.png">ActivateWindow(10040,"addons://all/xbmc.addon.video",return)</favourite>
</favourites>'''


def test_parse_reads_name_thumb_and_action():
    favs = fv.parse(XML)
    assert [f['thumb'] for f in favs] == ['https://image.tmdb.org/t/p/w500/hack.jpg',
                                          'http://addonbg.co/black/img/deportes.png',
                                          'https://image.tmdb.org/t/p/w500/fmsb.jpg', 'DefaultAddonVideo.png']
    assert favs[0]['action'] == 'ActivateWindow(10025,"plugin://plugin.video.palantir3/?abc",return)'
    assert favs[1]['action'] == 'ActivateWindow(10025,"plugin://plugin.video.blackghost/?mode=17&url=x",return)'


def test_parse_survives_empty_or_broken_files():
    assert fv.parse('') == [] and fv.parse('<favourites>') == []


def test_title_and_year_come_from_the_palantir_label():
    favs = fv.parse(XML)
    assert fv.title_year(favs[0]['name']) == ('The Hack', '2025')
    assert fv.title_year(favs[2]['name']) == ('Father Mother Sister Brother', '2025')
    assert fv.title_year(favs[1]['name']) == ('AGENDA STREAMTP', '')
    assert fv.title_year('Add-ons de vídeo') == ('Add-ons de vídeo', '')


def test_target_opens_folders_plays_media_and_runs_the_rest():
    assert fv.target('ActivateWindow(10025,"plugin://p/?a=1&b=2",return)') == ('folder', 'plugin://p/?a=1&b=2')
    assert fv.target('ActivateWindow(Videos,"addons://all/xbmc.addon.video",return)') == (
        'folder', 'addons://all/xbmc.addon.video')
    assert fv.target('PlayMedia("plugin://p/?play=1")') == ('play', 'plugin://p/?play=1')
    assert fv.target('RunScript(script.foo)') == ('builtin', 'RunScript(script.foo)')


def test_search_url_asks_tmdb_in_spanish_for_movies_and_series_at_once():
    url = urlparse(fv.search_url('La Casa del Dragón', 'K'))
    assert url.path == '/3/search/multi'
    assert parse_qs(url.query) == {'query': ['La Casa del Dragón'], 'language': ['es-ES'], 'api_key': ['K']}


MULTI = {'results': [
    {'media_type': 'person', 'id': 1, 'name': 'The Hack'},
    {'media_type': 'movie', 'id': 10, 'title': 'The Hack', 'release_date': '2019-03-01', 'backdrop_path': '/m.jpg'},
    {'media_type': 'tv', 'id': 20, 'name': 'The Hack', 'first_air_date': '2025-09-24', 'backdrop_path': '/tv.jpg',
     'poster_path': '/p.jpg', 'overview': 'Dos periodistas…'},
]}


def test_pick_matches_the_year_before_the_type():
    info = fv.pick(MULTI['results'], 'The Hack', '2025', 'movie')
    assert info == {'kind': 'tv', 'tmdb_id': 20, 'title': 'The Hack', 'year': '2025', 'plot': 'Dos periodistas…',
                    'fanart': fv.IMAGES + '/w1280/tv.jpg', 'poster': fv.IMAGES + '/w500/p.jpg'}


def test_pick_uses_the_hint_when_the_year_does_not_decide():
    assert fv.pick(MULTI['results'], 'The Hack', '', 'movie')['tmdb_id'] == 10
    assert fv.pick(MULTI['results'], 'The Hack', '', 'tv')['tmdb_id'] == 20
    assert fv.pick(MULTI['results'], 'Otra cosa', '2025', 'tv') is None  # el título tiene que coincidir
    assert fv.pick([], 'The Hack', '2025', 'tv') is None


class FakeGet:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, url):
        self.calls.append(url)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_lookup_asks_tmdb_once_and_remembers():
    cache, get = {}, FakeGet(MULTI)
    fav = fv.parse(XML)[0]
    first = fv.lookup(fav, 'K', get, cache)
    assert first['tmdb_id'] == 20 and len(get.calls) == 1
    assert fv.lookup(fav, 'K', get, cache) == first and len(get.calls) == 1


def test_lookup_skips_favourites_without_year_and_does_not_remember_network_errors():
    favs = fv.parse(XML)
    get = FakeGet(MULTI)
    assert fv.lookup(favs[1], 'K', get, {}) is None and get.calls == []  # agenda de BlackGhost
    assert fv.lookup(favs[0], '', get, {}) is None and get.calls == []  # sin clave de TMDb
    cache = {}
    assert fv.lookup(favs[0], 'K', FakeGet(IOError('sin red')), cache) is None
    assert cache == {}  # se vuelve a intentar la próxima vez
    assert fv.lookup(favs[2], 'K', FakeGet({'results': []}), cache) is None
    assert list(cache.values()) == [None]  # TMDb no la tiene: no se pregunta más


def test_hint_comes_from_the_action():
    favs = fv.parse(XML)
    assert fv.hint(favs[0]['action']) == 'tv' and fv.hint(favs[2]['action']) == 'movie'
