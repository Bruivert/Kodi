from resources.lib import arte_deportes as ad

NATIONS = ['https://r2.thesportsdb.com/league/fanart/n1.jpg', 'https://r2.thesportsdb.com/league/fanart/n2.jpg']
ARTE = {'leagues': {'4490': {'ok': True, 'fanarts': NATIONS, 'time': 0},
                    '4496': {'ok': True, 'fanarts': ['https://x/afcon.jpg'], 'time': 0},
                    '4407': {'ok': False, 'fanarts': [], 'time': 0}},  # el número no era MotoGP
        }
SOCCER = 'https://www.thesportsdb.com/images/sports/soccer.jpg'
TENNIS = 'https://www.thesportsdb.com/images/sports/tennis.jpg'
MOTOR = 'https://www.thesportsdb.com/images/sports/motorsport.jpg'
BASKET = 'https://www.thesportsdb.com/images/sports/basketball.jpg'

BG_FANART = 'http://addonbg.co/black/img/fanart.jpg'


def item(label, plot='', fanart=''):
    art = {'thumb': 'http://addonbg.co/black/img/deportes.png'}
    if fanart:
        art['fanart'] = fanart
    return {'label': label, 'path': 'plugin://bg/?x', 'folder': False, 'art': art, 'info': {'plot': plot} if plot else {},
            'uniqueids': {}, 'properties': {}}


def test_competition_in_the_spanish_agenda_gives_its_fanart():
    url = ad.fanart_for(item('20:45 [B]Liga de Naciones de la UEFA:[/B] Gales vs Portugal Disney+'),
                        'deportes.agenda', ARTE)
    assert url in NATIONS


def test_each_match_keeps_the_same_image_but_matches_differ():
    a = item('20:45 Liga de Naciones de la UEFA: Gales vs Portugal')
    b = item('20:45 Liga de Naciones de la UEFA: Dinamarca vs Noruega')
    assert ad.fanart_for(a, 'deportes.agenda', ARTE) == ad.fanart_for(a, 'deportes.agenda', ARTE)
    urls = {ad.fanart_for(item('20:45 Liga de Naciones de la UEFA: %s vs X' % n), 'deportes.agenda', ARTE)
            for n in ('Gales', 'Dinamarca', 'Polonia', 'Suecia', 'Italia', 'Francia')}
    assert urls == set(NATIONS)
    assert b


def test_concacaf_nations_league_is_not_the_uefa_one():
    url = ad.fanart_for(item('20:00 Liga de Naciones de la CONCACAF: St. Kitts and Nevis vs Bonaire'),
                        'deportes.agenda', ARTE)
    assert url == SOCCER


def test_nsports_says_the_league_in_the_plot():
    url = ad.fanart_for(item('[COLOR red]LIVE[/COLOR] Lesotho vs. Gabon', 'League: Africa Cup of Nations Qualifying',
                             BG_FANART), 'deportes.futbol', ARTE)
    assert url == 'https://x/afcon.jpg'


def test_sport_when_there_is_no_known_competition():
    assert ad.fanart_for(item('14:00 A. Fils vs R. Jódar'), 'deportes.espana', ARTE) == TENNIS
    assert ad.fanart_for(item('20:30 Barça Basket vs Paris Basketball'), 'deportes.espana', ARTE) == BASKET
    assert ad.fanart_for(item('[24/7] DAZN F1'), 'deportes.motor', ARTE) == MOTOR  # la fila manda
    # MotoGP no se pudo comprobar en TheSportsDB: el deporte en su lugar.
    assert ad.fanart_for(item('MotoGP: GP de Valencia'), 'deportes.agenda', ARTE) == MOTOR


def test_football_when_nothing_is_known():
    assert ad.fanart_for(item('18:00 Croacia vs España'), 'deportes.espana', ARTE) == SOCCER
    assert ad.fanart_for(item('DAZN'), 'deportes.canales', ARTE) == SOCCER
    # Las del deporte no necesitan pedir nada: están desde el primer momento.
    assert ad.fanart_for(item('18:00 Croacia vs España'), 'deportes.espana', {}) == SOCCER


def test_sport_images_follow_thesportsdb_names():
    assert ad.sport_image('American Football') == 'https://www.thesportsdb.com/images/sports/american_football.jpg'
    assert ad.sport_image('Ice Hockey') == 'https://www.thesportsdb.com/images/sports/ice_hockey.jpg'


def test_apply_replaces_only_missing_or_blackghost_generic_fanart():
    items = [item('Gales vs Portugal (Liga de Naciones de la UEFA)'), item('LIVE Lesotho vs. Gabon', '', BG_FANART),
             item('Final', '', 'https://otra/propia.jpg')]
    out = ad.apply(items, 'deportes.futbol', ARTE)
    assert out[0]['art']['fanart'] in NATIONS
    assert out[1]['art']['fanart'] == SOCCER
    assert out[2]['art']['fanart'] == 'https://otra/propia.jpg'  # la que trae BlackGhost se respeta
    assert 'fanart' not in items[0]['art']  # no toca la copia guardada


# --- Qué pedir a TheSportsDB (clave gratuita: muy pocas peticiones) ---

def test_next_request_asks_each_league_once_a_week():
    first = ad.next_request({}, now=1000)
    assert first == str(ad.LEAGUES[0][0])
    state = {'leagues': {str(l[0]): {'ok': True, 'fanarts': [], 'time': 1000} for l in ad.LEAGUES}}
    assert ad.next_request(state, now=1000 + 3600) is None
    assert ad.next_request(state, now=1000 + ad.MAX_AGE) == str(ad.LEAGUES[0][0])


def test_league_answer_is_used_only_if_it_is_the_expected_competition():
    nations = {'leagues': [{'strLeague': 'UEFA Nations League', 'strFanart1': NATIONS[0], 'strFanart2': NATIONS[1],
                            'strFanart3': None, 'strFanart4': ''}]}
    assert ad.read_league(nations, 'UEFA Nations League', now=5) == {'ok': True, 'fanarts': NATIONS, 'time': 5}
    other = {'leagues': [{'strLeague': 'Polish Ekstraklasa', 'strFanart1': 'https://x/p.jpg'}]}
    assert ad.read_league(other, 'MotoGP', now=5) == {'ok': False, 'fanarts': [], 'time': 5}
    assert ad.read_league({'leagues': None}, 'MotoGP', now=5)['ok'] is False


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def test_fetcher_goes_slowly_and_waits_an_hour_when_blocked():
    clock, state, asked = Clock(0), {}, []
    nations = {'leagues': [{'strLeague': 'UEFA Nations League', 'strFanart1': NATIONS[0]}]}

    def get(url):
        asked.append(url)
        if len(asked) == 2:
            raise IOError('HTTP Error 429: Too Many Requests')
        return nations
    f = ad.Fetcher(lambda: state, state.update, get, lambda: True, clock)
    assert f.tick() is None  # deja arrancar a Kodi
    clock.t += ad.START_DELAY
    assert f.tick() == '4490' and asked == [ad.API + 'lookupleague.php?id=4490']
    assert state['leagues']['4490'] == {'ok': True, 'fanarts': [NATIONS[0]], 'time': clock.t}
    assert f.tick() is None  # una petición por minuto como mucho
    clock.t += ad.GAP
    second = str(ad.LEAGUES[1][0])
    assert f.tick() == second and len(asked) == 2  # contesta 429
    clock.t += ad.GAP
    assert f.tick() is None  # bloqueado: espera una hora
    clock.t += ad.BLOCKED_WAIT
    assert f.tick() == second


# Partidos reales de BlackGhost del 17/11/2026 que salían con el fondo equivocado.
HOCKEY = 'https://www.thesportsdb.com/images/sports/ice_hockey.jpg'
HANDBALL = 'https://www.thesportsdb.com/images/sports/handball.jpg'
CHAMPIONS = {'leagues': {'4480': {'ok': True, 'fanarts': ['https://x/ucl.jpg'], 'time': 0}}}


def test_laliga_smartbank_was_the_second_division():
    arte = {'leagues': {'4400': {'ok': True, 'fanarts': ['https://x/l2.jpg'], 'time': 0},
                        '4335': {'ok': True, 'fanarts': ['https://x/l1.jpg'], 'time': 0}}}
    assert ad.fanart_for(item('[24/7] LaLiga SmartBank TV'), 'deportes.futbol', arte) == 'https://x/l2.jpg'
    assert ad.fanart_for(item('[24/7] DAZN LaLiga'), 'deportes.futbol', arte) == 'https://x/l1.jpg'


def test_hockey_champions_league_is_not_football():
    hockey = item('[B][COLOR red]LIVE[/COLOR][/B] Tappara vs Adler Mannheim',
                  'League: Hockey Champions League\n Category: FOOTBALL\n Status: LIVE NOW', BG_FANART)
    assert ad.fanart_for(hockey, 'deportes.futbol', CHAMPIONS) == HOCKEY


def test_the_channel_name_after_the_match_does_not_count():
    friendly = item('00:00 [B]Amistoso Internacional: Argentina vs Costa Rica[/B] '
                    '[COLORlightblue]Movistar Liga de Campeones[/COLOR]  ')
    assert ad.fanart_for(friendly, 'deportes.agenda', CHAMPIONS) == SOCCER
    final = item('20:20 [B]Champions League - Cuartos de final[/B]')
    assert ad.fanart_for(final, 'deportes.espana', CHAMPIONS) == 'https://x/ucl.jpg'


def test_basketball_and_handball_clubs_that_do_not_say_the_sport():
    def lab(match):
        return item('[COLOR lightblue][COLOR yellow]20:30[/COLOR][B] %s[/B][/COLOR]' % match)
    for match in ('Joventut Badalona vs FC Porto CB', 'Unicaja Málaga vs KVIS Pardubice',
                  'Olimpija Ljubljana vs San Pablo Burgos'):
        assert ad.fanart_for(lab(match), 'deportes.espana', {}) == BASKET, match
    assert ad.fanart_for(lab('BM Porriño vs Atlético Guardés'), 'deportes.espana', {}) == HANDBALL
    assert ad.fanart_for(lab('Celta Femenino vs Espanyol Femenino'), 'deportes.espana', {}) == SOCCER


def test_nsports_match_card_stays_on_the_card_and_the_photo_goes_to_the_background():
    card = 'https://nuviosports.xyz/img/match?cat=football&title=Lesotho+vs.+Gabon&shape=landscape&v=2'
    lesotho = item('LIVE Lesotho vs. Gabon', 'League: Africa Cup of Nations', BG_FANART)
    lesotho['art']['thumb'] = card
    out = ad.apply([lesotho, item('20:45 [B]Liga de Naciones de la UEFA: Gales vs Portugal[/B]')],
                   'deportes.futbol', ARTE)
    assert out[0]['art']['landscape'] == card and out[0]['art']['fanart'] == 'https://x/afcon.jpg'
    # Con solo el icono de BlackGhost, la tarjeta enseña la foto (no se le pone "landscape").
    assert 'landscape' not in out[1]['art'] and out[1]['art']['fanart'] in NATIONS
