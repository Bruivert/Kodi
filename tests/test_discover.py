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
    out = d.classify(entries, d.DEPORTES)
    assert out['nfl']['path'] == 'p://nfl'
    assert out['futbol']['path'] == 'p://futbol'


def test_classify_uses_each_entry_once():
    entries = [entry('Agenda de hoy - Fútbol', 'p://agenda')]
    out = d.classify(entries, d.DEPORTES)
    assert list(out) == ['agenda']


def test_classify_ignores_files_and_missing_categories():
    entries = [entry('Fútbol', 'p://futbol.mp4', filetype='file'), entry('UFC', 'p://ufc')]
    out = d.classify(entries, d.DEPORTES)
    assert out == {'ufc': {'label': 'UFC', 'path': 'p://ufc'}}


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
    BG: [entry('Cine', BG + '?c=cine'), entry('[COLOR lime]DEPORTES[/COLOR]', BG + '?c=dep')],
    BG + '?c=dep': [entry('Agenda', BG + '?d=agenda'), entry('Fútbol', BG + '?d=futbol'),
                    entry('Fútbol Americano', BG + '?d=nfl'), entry('NBA / Baloncesto', BG + '?d=basket'),
                    entry('Pádel', BG + '?d=padel'), entry('Fórmula 1', BG + '?d=f1'),
                    entry('MotoGP', BG + '?d=motogp'), entry('UFC', BG + '?d=ufc')],
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


def test_discover_blackghost_finds_every_sport_and_agenda():
    out = d.discover_blackghost(list_dir, find_addon, never_ask)
    assert out['id'] == 'plugin.video.blackghost'
    assert out['agenda']['path'] == BG + '?d=agenda'
    sports = out['deportes']
    assert [k for k in d.DEPORTES if k != 'agenda'] == list(sports)
    assert sports['nfl']['path'] == BG + '?d=nfl'
    assert sports['futbol']['path'] == BG + '?d=futbol'
    assert sports['baloncesto']['path'] == BG + '?d=basket'
    assert sports['f1']['path'] == BG + '?d=f1'


def test_unrecognised_required_folder_is_chosen_by_hand():
    tree = {BG: [entry('Zona Ghost', BG + '?c=x'), entry('Eventos en vivo', BG + '?c=ev')],
            BG + '?c=ev': [entry('UFC', BG + '?d=ufc')]}
    asked = []

    def ask(title, labels):
        asked.append((title, labels))
        return labels.index('Eventos en vivo')

    out = d.discover_blackghost(lambda p: tree.get(p, []), find_addon, ask)
    assert asked and 'Deportes' in asked[0][0]
    assert out['deportes'] == {'ufc': {'label': 'UFC', 'path': BG + '?d=ufc'}}


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
