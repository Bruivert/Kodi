from resources.lib.trailer_service import LogWatch, TrailerAutoplay, count_download_failures

# Líneas reales del kodi.log de la Vontar X4 cuando YouTube (cliente ANDROID_VR) corta el audio con 403.
FAIL = ('2026-11-16 16:49:14.698 T:17586   error <general>: AddOnLog: inputstream.adaptive: [AS-7] '
        'Download failed, HTTP error 403: http://127.0.0.1:50152/youtube/stream?expire=1\n')
RETRY = ('2026-11-16 16:49:15.199 T:17586 warning <general>: AddOnLog: inputstream.adaptive: [AS-7] '
         'Segment download failed, attempt 2...\n')
OTHER = ('2026-11-16 16:49:08.925 T:17570    info <general>: AddOnLog: inputstream.adaptive: '
         'Manifest successfully parsed (Periods: 1, Streams in first period: 8, Type: VOD)\n')


class FakeKodi:
    def __init__(self):
        self.labels = {'ListItem.DBType': 'movie', 'ListItem.UniqueID(tmdb)': '603',
                       'ListItem.IMDBNumber': 'tt0133093', 'ListItem.Title': 'Matrix', 'ListItem.Year': '1999'}
        self.conds = {'Window.IsActive(home)': True}
        self.now = 0.0

    def info(self, label):
        return self.labels.get(label, '')

    def cond(self, expr):
        return self.conds.get(expr, False)

    def clock(self):
        return self.now


class FakePlayer:
    def __init__(self):
        self.played, self.stopped, self.starts, self.playing = [], 0, 0, False
        self.pos, self.dur = 0.0, 0.0

    def position(self):
        return self.pos

    def duration(self):
        return self.dur

    def play(self, url):
        self.played.append(url)
        self.starts += 1
        self.playing = True

    def stop(self):
        self.stopped += 1
        self.playing = False

    def is_playing(self):
        return self.playing

    def started_count(self):
        return self.starts

    def playing_file(self):
        return self.played[-1] if self.playing and self.played else ''


class FakeWatch:
    def __init__(self):
        self.fails, self.marks = 0, 0

    def mark(self):
        self.marks += 1
        self.fails = 0

    def failures(self):
        return self.fails


def make(enabled=True, key='es1', on_resolve=None, watch=None):
    k, p = FakeKodi(), FakePlayer()
    calls = []
    k.closed = 0
    k.dims = []

    def resolve(kind, tmdb, imdb, title, year):
        calls.append((kind, tmdb, imdb, title, year))
        if on_resolve:
            on_resolve(k)
        return key(title) if callable(key) else key

    def close_error():
        k.closed += 1
        k.conds['Window.IsVisible(okdialog)'] = False

    s = TrailerAutoplay(k.info, k.cond, p, resolve, lambda: enabled, k.clock, watch=watch, close_error=close_error,
                        dim=k.dims.append)
    return s, k, p, calls


def run(s, k, seconds, step=0.5):
    end = k.now + seconds
    while k.now < end:
        s.tick()
        k.now += step
    s.tick()


def test_plays_spanish_trailer_after_four_seconds_not_before():
    s, k, p, calls = make()
    run(s, k, 3.5)
    assert p.played == []
    run(s, k, 1.0)
    assert p.played == ['plugin://plugin.video.youtube/play/?video_id=es1']
    assert calls == [('movie', '603', 'tt0133093', 'Matrix', '1999')]
    run(s, k, 10)
    assert len(p.played) == 1  # once per focus


def test_tvshow_uses_tv_kind_and_other_types_are_ignored():
    s, k, p, calls = make()
    k.labels['ListItem.DBType'] = 'tvshow'
    run(s, k, 5)
    assert calls[0][0] == 'tv'
    s, k, p, calls = make()
    k.labels['ListItem.DBType'] = ''  # sports channel / folder
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_focus_change_stops_our_trailer():
    s, k, p, _ = make()
    run(s, k, 5)
    k.labels['ListItem.Title'] = 'Otra'
    k.labels['ListItem.UniqueID(tmdb)'] = '604'
    s.tick()
    assert p.stopped == 1


def test_never_stops_dads_movie():
    s, k, p, _ = make()
    run(s, k, 5)
    p.play('plugin://plugin.video.palantir3/?play=movie')  # dad pressed play
    k.labels['ListItem.Title'] = 'Otra'
    s.tick()
    assert p.stopped == 0


def test_never_stops_while_fullscreen():
    s, k, p, _ = make()
    run(s, k, 5)
    k.conds['Window.IsActive(fullscreenvideo)'] = True
    k.conds['Window.IsActive(home)'] = False
    s.tick()
    assert p.stopped == 0


def test_does_not_start_when_something_else_plays():
    s, k, p, calls = make()
    p.playing = True
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_disabled_or_outside_menus_does_nothing():
    s, k, p, calls = make(enabled=False)
    run(s, k, 10)
    assert p.played == []
    s, k, p, calls = make()
    k.conds['Window.IsActive(home)'] = False
    run(s, k, 10)
    assert p.played == [] and calls == []


def test_no_spain_trailer_plays_nothing():
    s, k, p, calls = make(key=None)
    run(s, k, 10)
    assert p.played == [] and len(calls) == 1


def test_focus_moved_while_resolving_plays_nothing():
    def move(k):
        k.labels['ListItem.Title'] = 'Otra'
    s, k, p, _ = make(on_resolve=move)
    run(s, k, 5)
    assert p.played == []


def test_failed_trailer_is_forgotten_so_a_later_movie_is_never_stopped():
    s, k, p, _ = make()
    p.play = lambda url: p.played.append(url)  # YouTube fails: nothing starts
    run(s, k, 5)
    assert p.played and p.starts == 0
    run(s, k, 20)  # grace period passes with nothing playing
    p.starts, p.playing = 1, True  # dad's movie starts (windowed) while focus stays
    k.labels['ListItem.Title'] = 'Otra'
    s.tick()
    assert p.stopped == 0


def test_modal_dialog_stops_trailer_and_blocks_new_ones():
    s, k, p, _ = make()
    run(s, k, 5)
    k.conds['System.HasActiveModalDialog'] = True  # e.g. context menu "Añadir a favoritos"
    s.tick()
    assert p.stopped == 1
    p.played.clear()
    run(s, k, 10)
    assert p.played == []


def focus_on(k, title):
    k.labels['ListItem.Title'] = title
    k.labels['ListItem.UniqueID(tmdb)'] = str(sum(map(ord, title)))


def test_stalled_trailer_is_stopped_and_never_retried():
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    run(s, k, 5)
    assert len(p.played) == 1 and w.marks == 1
    w.fails = 1  # un fallo suelto puede ser pasajero
    s.tick()
    assert p.stopped == 0
    w.fails = 2  # YouTube sigue devolviendo 403: la imagen se congelaría
    s.tick()
    assert p.stopped == 1 and not p.playing
    focus_on(k, 'Otra')
    run(s, k, 1)
    focus_on(k, 'Matrix')  # vuelve a la misma película: no se repite el tráiler que se atascó
    k.labels['ListItem.UniqueID(tmdb)'] = '603'
    run(s, k, 10)
    assert len(p.played) == 1


def test_stalled_trailer_is_stopped_even_in_fullscreen():
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    run(s, k, 5)
    k.conds['Window.IsActive(fullscreenvideo)'] = True
    w.fails = 2
    s.tick()
    assert p.stopped == 1


def test_trailer_past_its_length_is_stopped():
    # Con el audio cortado Kodi sigue contando tiempo con la imagen congelada (369 s en un tráiler de 156 s).
    s, k, p, _ = make()
    run(s, k, 5)
    p.dur, p.pos = 156.0, 160.0
    s.tick()
    assert p.stopped == 0
    p.pos = 162.0
    s.tick()
    assert p.stopped == 1


def test_three_stalled_trailers_in_a_row_pause_autoplay():
    w = FakeWatch()
    s, k, p, _ = make(watch=w, key=lambda title: 'key-' + title)
    for n in range(3):
        focus_on(k, 'Peli %d' % n)
        run(s, k, 5)
        w.fails = 2
        s.tick()
    assert len(p.played) == 3 and p.stopped == 3
    focus_on(k, 'Peli 4')
    run(s, k, 10)
    assert len(p.played) == 3  # YouTube no funciona: no más tirones de 5 s en cada película


def test_a_trailer_that_plays_well_resets_the_streak():
    w = FakeWatch()
    s, k, p, _ = make(watch=w, key=lambda title: 'key-' + title)
    for n in range(2):
        focus_on(k, 'Mala %d' % n)
        run(s, k, 5)
        w.fails = 2
        s.tick()
    focus_on(k, 'Buena')
    run(s, k, 5)
    p.pos = 20.0  # suena bien un buen rato
    s.tick()
    p.pos = 0.0
    for n in range(2):
        focus_on(k, 'Mala bis %d' % n)
        run(s, k, 5)
        w.fails = 2
        s.tick()
    focus_on(k, 'Otra buena')
    run(s, k, 5)
    assert p.played[-1].endswith('key-Otra buena')


def test_count_download_failures_only_counts_real_failures():
    assert count_download_failures(OTHER + FAIL + RETRY + FAIL) == 2
    assert count_download_failures('') == 0


def test_logwatch_counts_only_lines_written_after_mark(tmp_path):
    log = tmp_path / 'kodi.log'
    log.write_text(FAIL + FAIL)  # fallos de antes de nuestro tráiler
    watch = LogWatch(str(log))
    watch.mark()
    assert watch.failures() == 0
    with open(str(log), 'a') as f:
        f.write(OTHER + FAIL[:40])  # Kodi está escribiendo la línea a medias
    assert watch.failures() == 0
    with open(str(log), 'a') as f:
        f.write(FAIL[40:] + RETRY + FAIL)
    assert watch.failures() == 2
    watch.mark()
    assert watch.failures() == 0


def test_logwatch_without_log_counts_nothing(tmp_path):
    watch = LogWatch(str(tmp_path / 'no-existe.log'))
    watch.mark()
    assert watch.failures() == 0


def youtube_still_preparing(p):
    p.play = lambda url: p.played.append(url)  # el tráiler tarda unos segundos en empezar


def youtube_starts(p):
    p.starts, p.playing = p.starts + 1, True


def test_loading_dialog_while_youtube_prepares_keeps_the_trailer_ours():
    # En la caja: Kodi enseña su "Cargando…" (diálogo modal) mientras YouTube prepara el vídeo. El servicio lo
    # tomaba por un cambio de foco, olvidaba el tráiler y luego no lo paraba ni congelado.
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    youtube_still_preparing(p)
    run(s, k, 5)
    assert len(p.played) == 1
    k.conds['System.HasActiveModalDialog'] = True
    run(s, k, 2)
    k.conds['System.HasActiveModalDialog'] = False
    youtube_starts(p)
    run(s, k, 2)
    w.fails = 2
    s.tick()
    assert p.stopped == 1


def test_focus_moved_before_trailer_started_stops_it_once_it_starts():
    s, k, p, _ = make()
    youtube_still_preparing(p)
    run(s, k, 5)
    focus_on(k, 'Otra')
    s.tick()
    assert p.stopped == 0  # todavía no hay nada que parar
    youtube_starts(p)
    s.tick()
    assert p.stopped == 1  # era el tráiler de la película anterior


def test_new_trailer_is_not_stopped_by_an_old_cancelled_one():
    s, k, p, _ = make(key=lambda title: 'key-' + title)
    youtube_still_preparing(p)
    run(s, k, 5)
    focus_on(k, 'Otra')
    run(s, k, 5)  # se pide el de "Otra"; Kodi solo reproduce la última petición
    assert p.played[-1].endswith('key-Otra')
    youtube_starts(p)
    run(s, k, 3)
    assert p.stopped == 0


def test_dads_movie_started_while_trailer_was_pending_is_never_stopped():
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    youtube_still_preparing(p)
    run(s, k, 5)
    p.played.append('plugin://plugin.video.palantir3/?play=movie')  # tu padre le da a una peli justo entonces
    p.starts, p.playing = 1, True
    w.fails = 2  # Palantir también puede apuntar fallos de descarga en el log
    s.tick()
    focus_on(k, 'Otra')
    s.tick()
    assert p.stopped == 0


def test_slow_youtube_open_beyond_grace_keeps_the_trailer_ours():
    # En la caja YouTube tardó 20 s en abrir un vídeo, con el "Cargando…" de Kodi encima todo el rato.
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    youtube_still_preparing(p)
    run(s, k, 5)
    p.playing = True  # Kodi ya lo está abriendo, pero aún no ha empezado
    k.conds['System.HasActiveModalDialog'] = True
    run(s, k, 20)
    k.conds['System.HasActiveModalDialog'] = False
    youtube_starts(p)
    run(s, k, 2)
    w.fails = 2
    s.tick()
    assert p.stopped == 1


def test_trailer_that_fails_to_open_closes_kodis_error_dialog_and_is_not_retried():
    # En la caja: YouTube tardó 21 s y falló al abrir; Kodi sacó "Error de reproducción" encima del menú.
    s, k, p, _ = make()
    youtube_still_preparing(p)
    run(s, k, 5)
    p.playing = True  # Kodi lo está abriendo
    run(s, k, 3)
    p.playing = False  # no pudo
    k.conds['Window.IsVisible(okdialog)'] = True
    run(s, k, 1)
    assert k.closed == 1
    focus_on(k, 'Otra')
    run(s, k, 1)
    focus_on(k, 'Matrix')
    k.labels['ListItem.UniqueID(tmdb)'] = '603'
    run(s, k, 10)
    assert len(p.played) == 1  # no se vuelve a intentar


def test_never_closes_dialogs_that_are_not_about_our_trailer():
    s, k, p, _ = make()
    run(s, k, 5)  # nuestro tráiler suena bien
    k.conds['Window.IsVisible(okdialog)'] = True  # un aviso cualquiera
    run(s, k, 2)
    assert k.closed == 0
    s, k, p, _ = make()
    youtube_still_preparing(p)
    run(s, k, 5)
    p.playing = True
    run(s, k, 3)
    p.playing = False
    run(s, k, 6)  # pasado el margen
    k.conds['Window.IsVisible(okdialog)'] = True
    run(s, k, 2)
    assert k.closed == 0


def test_trailer_stuck_while_opening_is_stopped():
    # En la caja: Kodi abrió el tráiler, se quedó en 00:00 sin llegar a empezar y llegaron los 403.
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    youtube_still_preparing(p)
    run(s, k, 5)
    p.playing = True  # abierto, pero sin empezar nunca
    run(s, k, 3)
    w.fails = 2
    s.tick()
    assert p.stopped == 1


def test_focus_moved_while_trailer_is_opening_stops_it_right_away():
    s, k, p, _ = make()
    youtube_still_preparing(p)
    run(s, k, 5)
    p.playing = True
    focus_on(k, 'Otra')
    s.tick()
    assert p.stopped == 1



def test_rows_fade_while_our_trailer_plays_and_come_back_when_it_stops():
    s, k, p, _ = make()
    run(s, k, 5)
    assert k.dims == []  # recién empezado: aún no
    p.pos = 2.0
    s.tick()
    assert k.dims == [True]
    run(s, k, 3)
    assert k.dims == [True]  # una sola vez
    focus_on(k, 'Otra')  # tu padre se mueve: se para el tráiler
    run(s, k, 1)
    assert k.dims == [True, False]


def test_rows_never_fade_for_dads_movie():
    s, k, p, _ = make()
    p.play('plugin://plugin.video.palantir3/?play=movie')
    p.pos = 30.0
    run(s, k, 10)
    assert k.dims == []


def test_rows_come_back_when_a_trailer_stalls():
    w = FakeWatch()
    s, k, p, _ = make(watch=w)
    run(s, k, 5)
    p.pos = 3.0
    s.tick()
    w.fails = 2
    run(s, k, 1)
    assert k.dims == [True, False]
