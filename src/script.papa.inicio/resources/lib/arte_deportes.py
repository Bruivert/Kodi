# -*- coding: utf-8 -*-
"""Fanart para las filas de Deportes: BlackGhost no trae imágenes (solo su icono), así que se ponen las de
TheSportsDB (base de datos libre de imágenes deportivas, la que usan los addons de Kodi).

- La de la competición, si el partido la nombra ("Liga de Naciones de la UEFA: Gales vs Portugal") o NSPORTS la dice
  en la sinopsis ("League: Africa Cup of Nations").
- Si no, la del deporte (tenis, baloncesto, motor…; la fila de Fútbol o de Motor ya lo dice), y si tampoco, la de
  fútbol, que es lo más habitual en la agenda.

Las del deporte son imágenes fijas de TheSportsDB (images/sports/<deporte>.jpg): no gastan peticiones. Las de las
competiciones sí: la clave gratuita deja muy pocas (429 a las ~10 seguidas; su lista de deportes solo trae 2), así
que el servicio pide una por minuto como mucho, las guarda una semana y, si le cortan, espera una hora. Puro: las
peticiones llegan inyectadas.
"""
import re
import zlib

from resources.lib.discover import clean, normalize

API = 'https://www.thesportsdb.com/api/v1/json/123/'
SPORT_IMAGES = 'https://www.thesportsdb.com/images/sports/%s.jpg'
BLACKGHOST_FANART = 'addonbg.co/black/img/fanart'  # su logo de neón: no es un fondo de deportes
BLACKGHOST_ICONS = ('addonbg.co/black/img/', 'Default')  # iconos, no imágenes del partido

# (id en TheSportsDB, nombre que debe devolver, deporte, palabras que la delatan). El orden es la prioridad: las más
# concretas primero ("La Liga 2" antes que "La Liga"). Los ids se comprueban por el nombre al pedirlos: si no
# coincide, no se usan (comprobados a mano el 17/11/2026: 4480, 4481, 5071, 4490, 4335, 4400, 4483, 4496, 4429).
LEAGUES = [
    (4490, 'UEFA Nations League', 'Soccer', ['liga de naciones de la uefa', 'uefa nations league']),
    (4480, 'UEFA Champions League', 'Soccer', ['champions league', 'liga de campeones', 'uefa champions']),
    (4481, 'UEFA Europa League', 'Soccer', ['europa league', 'uefa europa']),
    (5071, 'UEFA Conference League', 'Soccer', ['conference league']),
    (4400, 'Spanish La Liga 2', 'Soccer', ['laliga hypermotion', 'laliga smartbank', 'la liga 2', 'laliga 2',
                                               'segunda division']),
    (4335, 'Spanish La Liga', 'Soccer', ['laliga', 'la liga', 'primera division']),
    (4483, 'Copa del Rey', 'Soccer', ['copa del rey']),
    (4496, 'African Cup of Nations', 'Soccer', ['africa cup of nations', 'african cup', 'copa africa',
                                                 'copa de africa', 'afcon']),
    (4429, 'FIFA World Cup', 'Soccer', ['mundial', 'world cup', 'copa del mundo']),
    (4328, 'English Premier League', 'Soccer', ['premier league']),
    (4332, 'Italian Serie A', 'Soccer', ['serie a']),
    (4331, 'German Bundesliga', 'Soccer', ['bundesliga']),
    (4334, 'French Ligue 1', 'Soccer', ['ligue 1']),
    (4387, 'NBA', 'Basketball', ['nba']),
    (4408, 'Spanish Liga ACB', 'Basketball', ['acb', 'liga endesa']),
    (4391, 'NFL', 'American Football', ['nfl']),
    (4380, 'NHL', 'Ice Hockey', ['nhl']),
    (4370, 'Formula 1', 'Motorsport', ['formula 1', 'formula uno', 'f1']),
    (4407, 'MotoGP', 'Motorsport', ['motogp', 'moto gp']),
    (4443, 'UFC', 'Fighting', ['ufc']),
    (4464, 'ATP World Tour', 'Tennis', ['atp']),
    (4517, 'WTA Tour', 'Tennis', ['wta']),
]

# Deporte (como lo llama TheSportsDB) → palabras que lo delatan. Fútbol el último: "liga" o "copa" salen en todo.
SPORTS = [
    ('Tennis', ['tenis', 'tennis', 'atp', 'wta', 'copa davis', 'roland garros', 'wimbledon', 'us open']),
    # "CB" (club de baloncesto) y los clubes de la ACB que no dicen el deporte ("Unicaja Málaga vs KVIS Pardubice").
    ('Basketball', ['baloncesto', 'basket', 'nba', 'acb', 'euroliga', 'euroleague', 'eurobasket', 'liga endesa', 'cb',
                    'unicaja', 'joventut', 'baskonia', 'breogan', 'obradoiro', 'san pablo burgos', 'gran canaria',
                    'la laguna tenerife', 'lenovo tenerife', 'morabanc andorra', 'coviran granada', 'hiopos lleida',
                    'casademont zaragoza', 'bilbao basket', 'surne bilbao']),
    ('Motorsport', ['formula 1', 'f1', 'motogp', 'moto gp', 'moto2', 'moto3', 'motorsport', 'rally', 'nascar',
                    'indycar', 'superbike', 'dakar']),
    ('Fighting', ['ufc', 'mma', 'boxeo', 'boxing', 'wwe', 'aew', 'lucha']),
    ('American Football', ['nfl', 'futbol americano', 'american football', 'college football']),
    ('Ice Hockey', ['hockey', 'nhl']),
    ('Handball', ['balonmano', 'handball', 'bm']),  # "BM Porriño"
    ('Golf', ['golf', 'pga']),
    ('Cycling', ['ciclismo', 'cycling', 'tour de france', 'vuelta a espana', 'giro']),
    ('Rugby', ['rugby']),
    ('Baseball', ['mlb', 'beisbol', 'baseball']),
    ('Darts', ['dardos', 'darts']),
    ('Volleyball', ['voleibol', 'volleyball']),
]
ROW_SPORT = {'deportes.futbol': 'Soccer', 'deportes.motor': 'Motorsport'}
DEFAULT_SPORT = 'Soccer'
TENNIS_PLAYERS = re.compile(r'(?:^| )[a-z] [a-z]+ vs [a-z] [a-z]+')  # "a fils vs r jodar"

START_DELAY = 180  # s tras encender
GAP = 60  # s entre petición y petición
BLOCKED_WAIT = 3600  # s si TheSportsDB corta (429)
MAX_AGE = 7 * 24 * 3600  # s: las imágenes de una competición casi no cambian


def sport_image(sport):
    return SPORT_IMAGES % sport.lower().replace(' ', '_')


def _has(text, words):
    return any(re.search(r'(?:^| )' + re.escape(w) + r'(?: |$)', text) for w in words)


BOLD = re.compile(r'\[B\](.*?)\[/B\]', re.IGNORECASE)


def _text(item):
    """El partido (y la sinopsis de NSPORTS, que dice la competición), sin el canal: la agenda pone el partido en
    negrita y detrás el canal ("Movistar Liga de Campeones" no es la Champions)."""
    label = item.get('label', '')
    bold = clean(BOLD.search(label).group(1)) if BOLD.search(label) else ''
    match = bold if len(bold) > 6 else clean(label)  # NSPORTS solo pone en negrita "LIVE"
    return normalize('%s %s' % (match, (item.get('info') or {}).get('plot', '')))


def _sport(text):
    if TENNIS_PLAYERS.search(text):
        return 'Tennis'
    return next((name for name, words in SPORTS if _has(text, words)), None)


def _pick(urls, item):
    return urls[zlib.crc32(normalize(item.get('label', '')).encode('utf-8')) % len(urls)] if urls else ''


def fanart_for(item, row_key, arte):
    """El fondo para un partido o canal de BlackGhost."""
    text = _text(item)
    leagues = (arte or {}).get('leagues') or {}
    sport = _sport(text)  # primero el deporte: "Hockey Champions League" no es la Champions de fútbol
    for league_id, _, league_sport, words in LEAGUES:
        if (sport is None or sport == league_sport) and _has(text, words):
            got = leagues.get(str(league_id)) or {}
            if got.get('ok') and got.get('fanarts'):
                return _pick(got['fanarts'], item)
            sport = league_sport  # el número no era esa competición o no tiene imágenes: la del deporte
            break
    return sport_image(sport or ROW_SPORT.get(row_key) or DEFAULT_SPORT)


def apply(items, row_key, arte):
    """Copia de los elementos con fanart donde no lo hay (o es el logo de BlackGhost). La tarjeta que genera NSPORTS
    (escudos, competición, hora y canal) se queda en la tarjeta ("landscape"): si no, la skin pondría el fanart."""
    out = []
    for item in items:
        art = dict(item.get('art') or {})
        thumb = art.get('thumb') or ''
        if thumb and 'landscape' not in art and not any(icon in thumb for icon in BLACKGHOST_ICONS):
            art['landscape'] = thumb
        if not art.get('fanart') or BLACKGHOST_FANART in art['fanart']:
            url = fanart_for(item, row_key, arte)
            if url:
                art['fanart'] = url
        out.append(dict(item, art=art))
    return out


# --- Qué pedir a TheSportsDB ---

def next_request(state, now):
    """El id de la competición que toca pedir, o None si todas están al día."""
    leagues = (state or {}).get('leagues') or {}
    for league_id, _, _, _ in LEAGUES:
        got = leagues.get(str(league_id))
        if not got or now - got.get('time', 0) >= MAX_AGE:
            return str(league_id)
    return None


def request_url(league_id):
    return API + 'lookupleague.php?id=%s' % league_id


def read_league(answer, expected, now):
    league = ((answer or {}).get('leagues') or [{}])[0] or {}
    fanarts = [league.get('strFanart%d' % i) for i in range(1, 5)]
    if normalize(league.get('strLeague') or '') != normalize(expected):
        return {'ok': False, 'fanarts': [], 'time': now}
    return {'ok': True, 'fanarts': [u for u in fanarts if u], 'time': now}


def _expected(league_id):
    return next(name for lid, name, _, _ in LEAGUES if str(lid) == str(league_id))


class Fetcher(object):
    """Va llenando las imágenes desde el servicio, sin pasar del límite de la clave gratuita."""

    def __init__(self, load, save, http_get, can_run, clock):
        self.load, self.save, self.http_get, self.can_run, self.clock = load, save, http_get, can_run, clock
        self.next_time = clock() + START_DELAY

    def tick(self):
        now = self.clock()
        if now < self.next_time or not self.can_run():
            return None
        state = dict(self.load() or {})
        league_id = next_request(state, now)
        self.next_time = now + GAP
        if not league_id:
            return None
        try:
            answer = self.http_get(request_url(league_id))
        except Exception as exc:
            if '429' in str(exc) or '1015' in str(exc):
                self.next_time = now + BLOCKED_WAIT
            return league_id
        leagues = dict(state.get('leagues') or {})
        leagues[league_id] = read_league(answer, _expected(league_id), now)
        state['leagues'] = leagues
        self.save(state)
        return league_id
