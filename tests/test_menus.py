import json

from resources.lib import menus as m

# Key sets observed in every Arctic Fuse 3 preset (shortcuts/presets/*/*.json, omega 3.5.1)
HUB_KEYS = {'label', 'icon', 'path', 'target', 'window', 'slot', 'disabled'}
ITEM_KEYS = {'label', 'icon', 'path', 'target'}

PAL = 'plugin://plugin.video.palantir3/'
BG = 'plugin://plugin.video.blackghost/'


def it(label, path):
    return {'label': label, 'path': path}


RUTAS = {
    'palantir': {
        'id': 'plugin.video.palantir3',
        'peliculas': {'estrenos': it('Estrenos', PAL + 'p_new'), 'populares': it('Populares', PAL + 'p_pop'),
                      'valoradas': it('Mejor valoradas', PAL + 'p_top'), 'generos': it('Géneros', PAL + 'p_gen')},
        'series': {'novedades': it('Novedades', PAL + 's_new'), 'emision': it('En emisión', PAL + 's_air'),
                   'populares': it('Populares', PAL + 's_pop'), 'valoradas': it('Mejor valoradas', PAL + 's_top')},
    },
    'blackghost': {
        'id': 'plugin.video.blackghost',
        'agenda': it('Agenda', BG + 'agenda'),
        'deportes': {'futbol': it('Fútbol', BG + 'futbol'), 'nfl': it('NFL', BG + 'nfl'),
                     'baloncesto': it('NBA', BG + 'nba'), 'padel': it('Pádel', BG + 'padel'),
                     'f1': it('F1', BG + 'f1'), 'motogp': it('MotoGP', BG + 'motogp'), 'ufc': it('UFC', BG + 'ufc')},
    },
}


def f(name):
    return 'skinvariables-shortcut-%s.json' % name


def test_all_items_have_arctic_fuse_keys():
    files = m.build_preset(RUTAS)
    for name, items in files.items():
        for item in items:
            keys = set(item)
            if name == f('hubs'):
                assert keys == HUB_KEYS, name
            else:
                assert ITEM_KEYS <= keys <= ITEM_KEYS | {'widget_style'}, name


def test_enabled_hubs_are_the_five_sections_in_spanish():
    hubs = m.build_preset(RUTAS)[f('hubs')]
    enabled = [(h['window'], h['label']) for h in hubs if h['disabled'] != 'True']
    assert enabled == [('1101', 'Películas'), ('1102', 'Series'), ('1103', 'Novedades'),
                       ('1104', 'Deportes'), ('1109', 'Favoritos')]
    assert {h['window'] for h in hubs} == {'1101', '1102', '1103', '1104', '1106', '1107', '1108', '1109'}


def test_favoritos_hub_shows_kodi_favourites():
    files = m.build_preset(RUTAS)
    assert [w['path'] for w in files[f('1109widgets')]] == ['favourites://']
    assert 'favourites://' in [w['path'] for w in files[f('homewidgets')]]


def test_sports_rows_follow_dad_order_with_agenda_first():
    rows = m.build_preset(RUTAS)[f('1104widgets')]
    assert [r['label'] for r in rows] == ['Agenda de hoy', 'Fútbol', 'Baloncesto', 'NFL', 'Pádel',
                                          'Fórmula 1', 'MotoGP', 'UFC']
    sub = m.build_preset(RUTAS)[f('1104submenu')]
    assert [s['path'] for s in sub] == [r['path'] for r in rows]


def test_movies_rows_are_posters_from_palantir():
    rows = m.build_preset(RUTAS)[f('1101widgets')]
    assert [(r['label'], r['path']) for r in rows] == [
        ('Estrenos', PAL + 'p_new'), ('Populares', PAL + 'p_pop'), ('Mejor valoradas', PAL + 'p_top')]
    assert all(r['widget_style'] == 'Poster' and r['target'] == 'videos' for r in rows)


def test_missing_sport_has_no_row():
    rutas = json.loads(json.dumps(RUTAS))
    del rutas['blackghost']['deportes']['padel']
    del rutas['blackghost']['agenda']
    labels = [r['label'] for r in m.build_preset(rutas)[f('1104widgets')]]
    assert 'Pádel' not in labels and 'Agenda de hoy' not in labels
    assert labels[0] == 'Fútbol'


def test_empty_rutas_only_favoritos_enabled():
    files = m.build_preset({})
    enabled = [h['window'] for h in files[f('hubs')] if h['disabled'] != 'True']
    assert enabled == ['1109']
    assert files[f('1101widgets')] == []
    assert files[f('homewidgets')] == [{'label': 'Mis favoritos', 'icon': '', 'path': 'favourites://',
                                        'target': 'videos'}]


def test_builtins_set_imdb_ratings_and_copy_preset():
    b = m.skin_builtins(RUTAS, 'special://profile/addon_data/script.papa.inicio/preset', '2026-11-16_10:00:00')
    assert 'Skin.SetString(CustomRating.Movies.Item01,IMDb)' in b
    assert 'Skin.SetString(CustomRating.TVShows.Item01,IMDb)' in b
    assert 'Skin.Reset(TMDbHelper.DisableRatings)' in b
    copy = ('RunScript(script.skinvariables,copy_menufolder=special://profile/addon_data/'
            'script.papa.inicio/preset/,skin=skin.arctic.fuse.3,force=True)')
    assert copy in b
    assert b.index(copy) < b.index('Skin.SetString(Shortcuts.RebuildDateTime,2026-11-16_10:00:00)')
    assert 'Skin.Reset(SetupWizard.Pending)' in b
    assert 'Skin.SetString(HomeSwitcher.1109.Type,Custom)' in b


def test_builtins_spotlight_uses_palantir_and_resets_missing():
    b = m.skin_builtins(RUTAS, 'x/', 'now')
    assert 'Skin.SetString(HomeSwitcher.Home.Spotlight.Path,"%sp_new")' % PAL in b
    assert 'Skin.SetString(HomeSwitcher.1104.Spotlight.Path,"%sagenda")' % BG in b
    b2 = m.skin_builtins({}, 'x/', 'now')
    assert 'Skin.Reset(HomeSwitcher.Home.Spotlight.Path)' in b2
    assert not any(s.startswith('Skin.SetString(HomeSwitcher.Home.Spotlight.Path') for s in b2)


def test_write_preset_writes_json_files():
    out = {}
    m.write_preset({f('hubs'): [{'label': 'Películas'}]}, 'dir', lambda p, t: out.__setitem__(p, t))
    assert list(out) == ['dir/' + f('hubs')]
    assert json.loads(out['dir/' + f('hubs')]) == [{'label': 'Películas'}]
