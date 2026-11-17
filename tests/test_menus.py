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
                     'baloncesto': it('Basketball', BG + 'nba'), 'espana': it('CIRACO', BG + 'ciraco'),
                     'f1': it('F1 Replays', BG + 'f1'), 'motor': it('Motorsport', BG + 'motor'),
                     'ufc': it('UFC', BG + 'ufc'), 'canales': it('ACESTREAM MIXTO', BG + 'mixto'),
                     'padel': it('Pádel', BG + 'padel')},  # "padel" lo guardó una versión antigua: ya no sale
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
                assert ITEM_KEYS <= keys <= ITEM_KEYS | {'widget_style', 'widget_sortby'}, name


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
    assert [r['label'] for r in rows] == ['Agenda de hoy', 'Partidos en España', 'Fútbol', 'Baloncesto', 'NFL',
                                          'Motor: F1 y MotoGP', 'Fórmula 1 en español', 'UFC y boxeo',
                                          'Canales Acestream']
    sub = m.build_preset(RUTAS)[f('1104submenu')]
    assert [s['path'] for s in sub] == [r['path'] for r in rows]


def test_movies_rows_are_posters_from_palantir():
    rows = m.build_preset(RUTAS)[f('1101widgets')]
    assert [(r['label'], r['path']) for r in rows] == [
        ('Estrenos', PAL + 'p_new'), ('Populares', PAL + 'p_pop'), ('Mejor valoradas', PAL + 'p_top'),
        ('Géneros', PAL + 'p_gen')]
    assert all(r['widget_style'] == 'Poster' and r['target'] == 'videos' for r in rows[:3])
    assert 'widget_style' not in rows[3]


def test_submenus_only_in_deportes():
    files = m.build_preset(RUTAS)
    for win in ('1101', '1102', '1103', '1109'):
        assert files[f('%ssubmenu' % win)] == [], win
    assert [s['path'] for s in files[f('1104submenu')]] == [r['path'] for r in files[f('1104widgets')]]


def test_series_generos_row_last_only_when_palantir_has_it():
    rutas = json.loads(json.dumps(RUTAS))
    rutas['palantir']['series']['generos'] = it('Géneros', PAL + 's_gen')
    rows = m.build_preset(rutas)[f('1102widgets')]
    assert (rows[-1]['label'], rows[-1]['path']) == ('Géneros', PAL + 's_gen')
    assert 'Géneros' not in [r['label'] for r in m.build_preset(RUTAS)[f('1102widgets')]]


def test_missing_sport_has_no_row():
    rutas = json.loads(json.dumps(RUTAS))
    del rutas['blackghost']['deportes']['espana']
    del rutas['blackghost']['agenda']
    labels = [r['label'] for r in m.build_preset(rutas)[f('1104widgets')]]
    assert 'Partidos en España' not in labels and 'Agenda de hoy' not in labels
    assert labels[0] == 'Fútbol'


def test_empty_rutas_only_favoritos_enabled():
    files = m.build_preset({})
    enabled = [h['window'] for h in files[f('hubs')] if h['disabled'] != 'True']
    assert enabled == ['1109']
    assert files[f('1101widgets')] == []
    assert files[f('homewidgets')] == [{'label': 'Mis favoritos', 'icon': '', 'path': 'favourites://',
                                        'target': 'videos', 'widget_sortby': 'track'}]


def test_builtins_set_imdb_ratings_and_copy_preset():
    b = m.skin_builtins(RUTAS, 'special://profile/addon_data/script.papa.inicio/preset', '2026-11-16_10:00:00')
    assert 'Skin.SetString(CustomRating.Movies.Item01,IMDb)' in b
    assert 'Skin.SetString(CustomRating.TVShows.Item01,IMDb)' in b
    assert 'Skin.SetBool(TMDbHelper.DisableRatings,false)' in b
    copy = ('RunScript(script.skinvariables,copy_menufolder=special://profile/addon_data/'
            'script.papa.inicio/preset/,skin=skin.arctic.fuse.3,force=True)')
    assert copy in b
    assert b.index(copy) < b.index('Skin.SetString(Shortcuts.RebuildDateTime,2026-11-16_10:00:00)')
    assert 'Skin.SetBool(SetupWizard.Pending,false)' in b
    assert 'Skin.SetString(HomeSwitcher.1109.Type,Custom)' in b
    rebuild = ('RunScript(script.skinvariables,"run_executebuiltin=special://skin/shortcuts/'
               'skinvariables-build-templates.json",use_rules)')
    assert b[-1] == rebuild
    assert b.index('Skin.SetString(Shortcuts.RebuildDateTime,2026-11-16_10:00:00)') < b.index(rebuild)


def test_builtins_never_reset_switches():
    # Skin.Reset(x) solo limpia el texto x si existe uno con ese nombre y deja el interruptor x como estaba.
    # En la caja el asistente de AF3 se quedaba "pendiente" para siempre por eso.
    b = m.skin_builtins(RUTAS, 'x/', 'now', first_run=True)
    switches = ('SetupWizard.Pending', 'TMDbHelper.DisableRatings', 'DefaultConfig.InitDone')
    assert not [s for s in b if s.startswith('Skin.Reset(') and s[11:-1] in switches]


def test_builtins_name_home_inicio():
    # AF3 guarda "$LOCALIZE[10000]" tal cual y lo enseña así en el menú.
    assert 'Skin.SetString(HomeSwitcher.Home.Name,Inicio)' in m.skin_builtins(RUTAS, 'x/', 'now')


def test_builtins_finish_af3_first_run_only_when_it_did_not():
    copy = 'RunScript(script.skinvariables,copy_menufolder=x/,skin=skin.arctic.fuse.3,force=True)'
    b = m.skin_builtins(RUTAS, 'x/', 'now', first_run=True)
    assert 'Skin.SetBool(DefaultConfig.InitDone)' in b
    assert 'Skin.SetBool(TMDbHelper.Service)' in b
    assert b.index('Skin.SetBool(DefaultConfig.InitDone)') < b.index(copy)
    normal = m.skin_builtins(RUTAS, 'x/', 'now')
    assert 'Skin.SetBool(DefaultConfig.InitDone)' not in normal
    assert 'Skin.SetBool(TMDbHelper.Service)' not in normal


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


def test_rows_have_a_fixed_order_so_kodi_does_not_reload_them_with_every_trailer():
    # Kodi recarga las filas "sin orden" cada vez que empieza o acaba una reproducción; con las de Palantir eso
    # tenía la CPU ocupada 15 s y el siguiente tráiler esperaba. Con un orden fijo no las recarga.
    files = m.build_preset(RUTAS)
    rows = [item for name, items in files.items() if name.endswith('widgets.json') for item in items]
    assert rows and all(r.get('widget_sortby') == 'track' for r in rows)


def test_menu_version_marks_changes_that_must_reach_existing_boxes():
    assert m.MENU_VERSION >= 2


def test_menu_version_marks_the_rows_without_trakt():
    assert m.MENU_VERSION >= 3


# Rutas de Palantir 3.3.11 tal como las encuentra ahora el asistente (sin las listas que piden Trakt).
RUTAS_SIN_TRAKT = {'palantir': {
    'id': 'plugin.video.palantir3',
    'peliculas': {'estrenos': it('Novedades', PAL + 'p_new'), 'recientes': it('Últimas añadidas', PAL + 'p_add'),
                  'generos': it('Por géneros', PAL + 'p_gen')},
    'series': {'novedades': it('Últimas actualizaciones', PAL + 's_upd'), 'nuevas': it('Nuevas series', PAL + 's_new'),
               'generos': it('Por géneros', PAL + 's_gen')},
}}


def test_rows_use_recently_added_movies_and_new_series():
    files = m.build_preset(RUTAS_SIN_TRAKT)
    assert [(r['label'], r['path']) for r in files[f('1101widgets')]] == [
        ('Estrenos', PAL + 'p_new'), ('Recién añadidas', PAL + 'p_add'), ('Géneros', PAL + 'p_gen')]
    assert [(r['label'], r['path']) for r in files[f('1102widgets')]] == [
        ('Nuevos episodios', PAL + 's_upd'), ('Nuevas series', PAL + 's_new'), ('Géneros', PAL + 's_gen')]
    assert all(r['widget_style'] == 'Poster' for r in files[f('1101widgets')][:2] + files[f('1102widgets')][:2])


def test_spotlights_name_the_list_they_show():
    b = m.skin_builtins(RUTAS_SIN_TRAKT, 'x/', 'now')
    assert 'Skin.SetString(HomeSwitcher.1101.Spotlight.Path,"%sp_add")' % PAL in b
    assert 'Skin.SetString(HomeSwitcher.1101.Spotlight.Label,Recién añadidas)' in b
    assert 'Skin.SetString(HomeSwitcher.1102.Spotlight.Path,"%ss_new")' % PAL in b
    assert 'Skin.SetString(HomeSwitcher.1102.Spotlight.Label,Nuevas series)' in b
    assert 'Skin.SetString(HomeSwitcher.Home.Spotlight.Label,Estrenos)' in b


def test_saved_trakt_only_lists_are_left_out():
    # Una caja montada con una versión anterior guardó "Más vistas" como Populares.
    rutas = json.loads(json.dumps(RUTAS))
    rutas['palantir']['peliculas']['populares'] = it('Más vistas', PAL + 'p_most')
    rutas['palantir']['series']['populares'] = it('Más vistas', PAL + 's_most')
    files = m.build_preset(rutas)
    paths = [r['path'] for name, rows in files.items() for r in rows]
    assert PAL + 'p_most' not in paths and PAL + 's_most' not in paths
    b = m.skin_builtins(rutas, 'x/', 'now')
    assert not [x for x in b if 'p_most' in x or 's_most' in x]
    assert 'Skin.SetString(HomeSwitcher.1101.Spotlight.Label,Estrenos)' in b
