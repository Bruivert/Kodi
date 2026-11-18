from resources.lib import buscar


RUTAS = {'palantir': {'buscar': {'peliculas': 'plugin://p/?pelis', 'series': 'plugin://p/?series'}}}


def test_choices_are_the_searches_palantir_has():
    assert buscar.choices(RUTAS) == [('peliculas', 'Películas', 'plugin://p/?pelis'),
                                     ('series', 'Series', 'plugin://p/?series')]
    assert buscar.choices({'palantir': {'buscar': {'series': 'plugin://p/?s'}}}) == [
        ('series', 'Series', 'plugin://p/?s')]
    assert buscar.choices({}) == []


def test_palantirs_repeat_mark_is_cleared_before_opening_its_search():
    # Con la marca puesta (la deja cualquier búsqueda con resultados), Palantir no saca el teclado y repite la
    # última búsqueda, aunque fuera de películas y ahora se pidan series.
    assert buscar.open_commands('plugin://p/?pelis') == (
        'ClearProperty(p3_play,10000)', 'ActivateWindow(videos,"plugin://p/?pelis",return)')


class Clock:
    def __init__(self):
        self.t = 0.0

    def sleep(self, seconds):
        self.t += seconds


def test_autofill_waits_for_palantirs_keyboard_and_types_once():
    clock, sent = Clock(), []
    opens_at = 3.5  # lo que tarda Palantir en sacar su teclado en la caja

    assert buscar.autofill(lambda: clock.t >= opens_at, sent.append, clock.sleep, 'allen') is True
    assert sent == ['allen'] and opens_at <= clock.t < opens_at + 1


def test_autofill_gives_up_if_the_keyboard_never_appears():
    clock, sent = Clock(), []
    assert buscar.autofill(lambda: False, sent.append, clock.sleep, 'allen') is False
    assert sent == [] and clock.t >= buscar.WAIT



def test_wait_for_returns_the_first_answer_or_none_at_the_limit():
    clock = Clock()
    assert buscar.wait_for(lambda: 'ok' if clock.t >= 2 else None, clock.sleep) == 'ok' and 2 <= clock.t < 2.5
    clock = Clock()
    assert buscar.wait_for(lambda: None, clock.sleep, limit=5) is None and clock.t >= 5


PATH = 'plugin://p/?series'


def test_after_search_waits_while_palantir_loads_or_shows_its_notice():
    assert buscar.after_search(True, True, PATH, '', PATH) is None  # "Cargando…" o el aviso de Palantir
    assert buscar.after_search(True, False, PATH, '', PATH) is None  # aún sin la lista
    assert buscar.after_search(True, False, PATH, '0', PATH) is None


def test_after_search_sees_the_results():
    assert buscar.after_search(True, False, PATH, '9', PATH) == 'ok'
    assert buscar.after_search(True, False, PATH + '/', '1', PATH) == 'ok'


def test_after_search_sees_kodi_falling_back_to_its_video_library():
    # Sin resultados, Palantir avisa y Kodi se queda en "Archivos / Listas de reproducción / Add-ons de vídeo".
    assert buscar.after_search(True, False, '', '3', PATH) == 'empty'


def test_after_search_stops_if_the_user_went_elsewhere():
    assert buscar.after_search(False, False, '', '', PATH) == 'away'
