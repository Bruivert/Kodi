from resources.lib import discover as d


def entry(label, path, filetype='directory'):
    return {'label': label, 'file': path, 'filetype': filetype}


# --- normalize / matches -------------------------------------------------

def test_normalize_strips_kodi_markup_accents_and_case():
    assert d.normalize('[COLOR gold][B]Fútbol[/B][/COLOR]') == 'futbol'
    assert d.normalize('  Pádel  —  EN DIRECTO ') == 'padel en directo'
    assert d.normalize('[UPPERCASE]Fórmula 1[/UPPERCASE] 🏎') == 'formula 1'


def test_matches_uses_word_boundaries_for_short_tokens():
    assert d.matches('F1 - Gran Premio', ['f1'])
    assert not d.matches('Canal HF1X', ['f1'])
    assert d.matches('[B]NBA[/B]', ['nba'])


def test_matches_respects_exclude():
    assert not d.matches('Fútbol Americano', ['futbol'], exclude=['americano'])
    assert d.matches('Fútbol', ['futbol'], exclude=['americano'])


# --- classify ------------------------------------------------------------

def test_classify_sends_futbol_americano_to_nfl_not_futbol():
    entries = [entry('Fútbol Americano', 'p://nfl'), entry('[COLOR red]Fútbol[/COLOR]', 'p://futbol')]
    out = d.classify(entries, d.NSPORTS)
    assert out['nfl']['path'] == 'p://nfl'
    assert out['futbol']['path'] == 'p://futbol'


def test_classify_uses_each_entry_once():
    entries = [entry('Fútbol y baloncesto', 'p://mix')]
    assert list(d.classify(entries, d.NSPORTS)) == ['futbol']


def test_classify_ignores_files_and_missing_categories():
    entries = [entry('Fútbol', 'p://futbol.mp4', filetype='file'), entry('MMA / UFC / Box', 'p://ufc')]
    assert d.classify(entries, d.NSPORTS) == {'ufc': {'label': 'MMA / UFC / Box', 'path': 'p://ufc'}}


# --- discover with fake addon trees -------------------------------------

PAL = 'plugin://plugin.video.palantir3/'
BG = 'plugin://plugin.video.blackghost/'

TREE = {
    PAL: [entry('[B]Películas[/B]', PAL + '?m=pelis'), entry('Series', PAL + '?m=series'),
          entry('Buscar', PAL + '?m=search'), entry('Ajustes', PAL + '?m=settings')],
    PAL + '?m=pelis': [entry('Estrenos', PAL + '?m=p_new'), entry('Populares', PAL + '?m=p_pop'),
                       entry('Mejor valoradas', PAL + '?m=p_top'), entry('Géneros', PAL + '?m=p_gen')],
    PAL + '?m=series': [entry('Populares', PAL + '?m=s_pop'), entry('En emisión', PAL + '?m=s_air'),
                        entry('Mejor valoradas', PAL + '?m=s_top'), entry('Novedades', PAL + '?m=s_new')],
    BG: [entry('INGRESAR AL ADDON', BG + '?entrar'), entry('Telegram:  @AddonBG', BG + '?tg', 'file')],
    BG + '?entrar': [entry('B L A C K G H O S T', BG + '?na'), entry('Deportes', BG + '?dep'),
                     entry('Cine', BG + '?cine'), entry('Agendas + Canales [B]● Acestreams[/B]', BG + '?ace')],
    BG + '?dep': [entry('»» BUSCAR EVENTO', BG + '?buscar'), entry('CANALES DEPORTES+', BG + '?canales'),
                  entry('[COLOR lime]AGENDA NSPORTS[/COLOR] ★★★', BG + '?nsports'),
                  entry('AGENDA LIVE ★★★', BG + '?live'),
                  entry('AGENDA DEPORTESPLUS+  st723  ★★', BG + '?dplus_latam'),
                  entry('AGENDA DEPORTESPLUS  st723  ★', BG + '?dplus'),
                  entry('Formula 1 Replays', BG + '?f1'), entry('Dazn F1 Opcion 1', BG + '?dazn', 'file')],
    BG + '?nsports': [entry('EN VIVO AHORA', BG + '?ns_live'), entry('Fútbol', BG + '?ns_futbol'),
                      entry('Basketball', BG + '?ns_basket'), entry('Fútbol Americano', BG + '?ns_nfl'),
                      entry('Tenis', BG + '?ns_tenis'), entry('Motorsport', BG + '?ns_motor'),
                      entry('MMA / UFC / Box', BG + '?ns_ufc')],
    BG + '?ace': [entry('► ACESTREAMID', BG + '?aceid'), entry('►  ACESTREAMᵅ    KS', BG + '?ks'),
                  entry('►  ACESTREAMᵅ    MIXTO', BG + '?mixto'),
                  entry('►  AGENDA DEL DIA   ArenaView', BG + '?arena'),
                  entry('►  AGENDA DEL DIA   CIRACO', BG + '?ciraco')],
}

ADDONS = {'palantir': 'plugin.video.palantir3', 'black ghost': 'plugin.video.blackghost'}


def list_dir(path):
    return TREE.get(path, [])


def find_addon(keywords):
    for k in keywords:
        if k in ADDONS:
            return ADDONS[k]
    return None


def never_ask(title, labels):
    raise AssertionError('ask should not be called: %s' % title)


def test_discover_palantir_finds_all_lists():
    out = d.discover_palantir(list_dir, find_addon, never_ask)
    assert out['id'] == 'plugin.video.palantir3'
    assert out['peliculas']['estrenos']['path'] == PAL + '?m=p_new'
    assert out['peliculas']['populares']['path'] == PAL + '?m=p_pop'
    assert out['peliculas']['valoradas']['path'] == PAL + '?m=p_top'
    assert out['peliculas']['generos']['path'] == PAL + '?m=p_gen'
    assert out['series']['populares']['path'] == PAL + '?m=s_pop'
    assert out['series']['emision']['path'] == PAL + '?m=s_air'
    assert out['series']['valoradas']['path'] == PAL + '?m=s_top'
    assert out['series']['novedades']['path'] == PAL + '?m=s_new'


def test_discover_blackghost_enters_with_the_code_and_finds_every_row():
    out = d.discover_blackghost(list_dir, find_addon, never_ask)
    assert out['id'] == 'plugin.video.blackghost'
    # DEPORTESPLUS sin "+" va en hora de España; la "+" es la latina.
    assert out['agenda'] == {'label': 'AGENDA DEPORTESPLUS st723 ★', 'path': BG + '?dplus'}
    assert {k: v['path'] for k, v in out['deportes'].items()} == {
        'espana': BG + '?ciraco', 'futbol': BG + '?ns_futbol', 'baloncesto': BG + '?ns_basket',
        'nfl': BG + '?ns_nfl', 'motor': BG + '?ns_motor', 'f1': BG + '?f1', 'ufc': BG + '?ns_ufc',
        'canales': BG + '?mixto'}


def test_blackghost_agenda_falls_back_to_live_then_any_agenda():
    tree = dict(TREE)
    tree[BG + '?dep'] = [e for e in TREE[BG + '?dep'] if 'DEPORTESPLUS' not in e['label']]
    assert d.discover_blackghost(lambda p: tree.get(p, []), find_addon, never_ask)['agenda']['path'] == BG + '?live'
    tree[BG + '?dep'] = [entry('AGENDA ZICO ★★', BG + '?zico')]
    assert d.discover_blackghost(lambda p: tree.get(p, []), find_addon, never_ask)['agenda']['path'] == BG + '?zico'


def test_blackghost_without_the_entry_screen_looks_in_its_root():
    tree = {BG: [entry('Cine', BG + '?cine'), entry('[COLOR lime]DEPORTES[/COLOR]', BG + '?dep')],
            BG + '?dep': [entry('AGENDA LIVE', BG + '?live')]}
    out = d.discover_blackghost(lambda p: tree.get(p, []), find_addon, never_ask)
    assert out['agenda']['path'] == BG + '?live' and out['deportes'] == {}


def test_blackghost_with_a_wrong_code_finds_nothing_and_does_not_ask_for_rows():
    tree = {BG: TREE[BG], BG + '?entrar': [entry('Código n16 inválido o inexistente', BG + '?na', 'file')]}
    asked = []
    out = d.discover_blackghost(lambda p: tree.get(p, []), find_addon, lambda t, l: asked.append(t) or -1)
    assert out == {'id': 'plugin.video.blackghost', 'deportes': {}}
    assert asked == []  # no hay carpetas entre las que elegir


def test_unrecognised_deportes_folder_is_chosen_by_hand():
    tree = {BG: [entry('Zona Ghost', BG + '?c=x'), entry('Eventos en vivo', BG + '?c=ev')],
            BG + '?c=ev': [entry('AGENDA LIVE', BG + '?live')]}
    asked = []

    def ask(title, labels):
        asked.append((title, labels))
        return labels.index('Eventos en vivo')

    out = d.discover_blackghost(lambda p: tree.get(p, []), find_addon, ask)
    assert asked and 'Deportes' in asked[0][0]
    assert out['agenda']['path'] == BG + '?live'


def test_skipping_required_folder_leaves_category_absent():
    tree = {BG: [entry('Zona Ghost', BG + '?c=x')]}
    out = d.discover_blackghost(lambda p: tree.get(p, []), find_addon, lambda t, l: -1)
    assert out['deportes'] == {}
    assert 'agenda' not in out


def test_missing_addon_returns_none():
    assert d.discover_palantir(list_dir, lambda k: None, never_ask) is None


# --- Palantir 3.3.11 tal como está en la caja (17/11/2026) ---

def _menu(prefix, labels):
    return [entry(label, PAL + '?%s=%d' % (prefix, i)) for i, label in enumerate(labels)]


REAL_PELIS = _menu('p', ['Novedades', 'Últimas añadidas', 'Recomendadas', 'Más vistas', 'Más vistas este mes', 'Sagas',
                         'Especiales', 'Buscar:', 'Por título', 'Por géneros', 'Por orden alfabético', 'Por año',
                         'Por calidad'])
REAL_SERIES = _menu('s', ['Últimas actualizaciones', 'Nuevas series', 'Series en seguimiento', 'Recomendadas',
                          'Más vistas', 'Más vistas este mes', 'Clásicas', 'Reality', 'Buscar:', 'Por título',
                          'Por géneros', 'Por año', 'Por orden alfabético'])
REAL_TREE = {PAL: [entry('Favoritos', PAL + '?m=fav'), entry('Películas', PAL + '?m=pelis'),
                   entry('Series', PAL + '?m=series'), entry('Listas Trakt.tv', PAL + '?m=trakt')],
             PAL + '?m=pelis': REAL_PELIS, PAL + '?m=series': REAL_SERIES}


def labels_of(group):
    return {key: item['label'] for key, item in group.items()}


def test_trakt_only_lists_are_recognised():
    for label in ('Más vistas', '[COLOR gold]Más vistas este mes[/COLOR]', 'Recomendadas', 'Series en seguimiento',
                  'Listas Trakt.tv'):
        assert d.needs_trakt(label), label
    for label in ('Novedades', 'Últimas añadidas', 'Nuevas series', 'Por géneros', 'Populares', ''):
        assert not d.needs_trakt(label), label


def test_real_palantir_rows_never_use_lists_that_need_trakt():
    # "Más vistas" pide una cuenta de Trakt: sin ella salían avisos que bloqueaban el mando y la fila quedaba vacía.
    out = d.discover_palantir(lambda p: REAL_TREE.get(p, []), find_addon, never_ask)
    assert labels_of(out['peliculas']) == {'estrenos': 'Novedades', 'recientes': 'Últimas añadidas',
                                           'generos': 'Por géneros'}
    assert labels_of(out['series']) == {'novedades': 'Últimas actualizaciones', 'nuevas': 'Nuevas series',
                                         'generos': 'Por géneros'}


def test_estrenos_is_not_the_recently_added_list_whatever_the_order():
    pelis = [entry('Últimas añadidas', PAL + '?p=add'), entry('Novedades', PAL + '?p=new')]
    out = d.classify(pelis, d.PELICULAS)
    assert out['estrenos']['path'] == PAL + '?p=new' and out['recientes']['path'] == PAL + '?p=add'


def test_palantir_search_by_title_is_found_for_the_magnifier():
    out = d.discover_palantir(lambda p: REAL_TREE.get(p, []), find_addon, never_ask)
    titles = {e['label']: e['file'] for e in REAL_PELIS}
    shows = {e['label']: e['file'] for e in REAL_SERIES}
    assert out['buscar'] == {'peliculas': titles['Por título'], 'series': shows['Por título']}
    # No es una fila: no entra en las listas que se copian ni se pintan.
    assert 'buscar' not in out['peliculas'] and 'buscar' not in out['series']
