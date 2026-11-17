# -*- coding: utf-8 -*-
"""Tráiler automático de fondo, como en Netflix: si el foco se queda quieto unos segundos
en una película o serie de los menús, suena su tráiler de España en segundo plano.

Todo llega inyectado (infolabels, condiciones, reproductor, reloj) para poder probarlo
sin Kodi; service.py conecta las piezas reales."""
import os

from resources.lib.trailers import youtube_url

WINDOWS = ('home', '1101', '1102', '1103', '1104', '1109')
KINDS = {'movie': 'movie', 'tvshow': 'tv'}
DELAY = 4.0
# YouTube (cliente ANDROID_VR del addon 7.4.4) corta a veces el audio con 403 a los pocos segundos. Kodi se
# queda con la imagen congelada y sigue contando tiempo, así que hay que mirar los fallos de descarga.
STALL_FAILS = 2     # fallos de descarga desde que empezó el tráiler: se ha atascado
OVERRUN = 5.0       # segundos de más sobre la duración: también atascado (red de seguridad)
MAX_STALLS = 3      # atascos seguidos: YouTube no funciona, se descansa un rato
PAUSE = 30 * 60.0   # la caja casi nunca se reinicia: la pausa no puede ser hasta el siguiente arranque
GOOD_AFTER = 15.0   # segundos sin fallos para dar YouTube por bueno otra vez
ERROR_WINDOW = 5.0  # si YouTube no pudo abrir nuestro tráiler, el "Error de reproducción" de Kodi sale enseguida
DIM_AFTER = 1.5     # segundos de tráiler antes de atenuar las filas de carátulas


def count_download_failures(text):
    return sum(1 for line in text.splitlines() if 'inputstream.adaptive' in line and 'Download failed' in line)


class LogWatch(object):
    """Cuenta los fallos de descarga que Kodi apunta en kodi.log desde mark()."""

    def __init__(self, path):
        self.path, self.offset, self.count = path, 0, 0

    def mark(self):
        try:
            self.offset = os.path.getsize(self.path)
        except OSError:
            self.offset = 0
        self.count = 0

    def failures(self):
        try:
            with open(self.path, 'rb') as f:
                f.seek(self.offset)
                data = f.read()
        except OSError:
            return self.count
        complete = data[:data.rfind(b'\n') + 1]  # la última línea puede estar a medio escribir
        self.offset += len(complete)
        self.count += count_download_failures(complete.decode('utf-8', 'replace'))
        return self.count


class _NoWatch(object):
    def mark(self):
        pass

    def failures(self):
        return 0


class TrailerAutoplay(object):
    def __init__(self, info, cond, player, resolve, enabled, clock, delay=DELAY, watch=None, close_error=None,
                 dim=None):
        self.info, self.cond, self.player = info, cond, player
        self.resolve, self.enabled, self.clock, self.delay = resolve, enabled, clock, delay
        self.watch = watch or _NoWatch()
        self.close_error = close_error or (lambda: None)
        self.dim = dim or (lambda on: None)  # atenuar (True) o devolver (False) las filas mientras suena
        self.dimmed = False
        self.focus = None
        self.since = 0.0
        self.done_for = None
        self.expect = None  # nº de reproducciones que habrá cuando empiece nuestro tráiler
        self.key = None
        self.cancel = False  # el foco se fue antes de que empezara: pararlo en cuanto empiece
        self.opening = False  # Kodi está abriendo nuestro tráiler
        self.failed_at = None
        self.stalled = set()  # tráileres que se atascaron: no se repiten
        self.streak = 0
        self.gave_up_at = 0.0

    def _focus(self):
        if self.cond('System.HasActiveModalDialog'):
            return None
        if not any(self.cond('Window.IsActive(%s)' % w) for w in WINDOWS):
            return None
        kind = KINDS.get(self.info('ListItem.DBType'))
        if not kind:
            return None
        return (kind, self.info('ListItem.UniqueID(tmdb)'), self.info('ListItem.IMDBNumber'),
                self.info('ListItem.Title') or self.info('ListItem.Label'), self.info('ListItem.Year'))

    def _ours(self):
        # Nuestro es lo que suena o se está abriendo con el vídeo de YouTube que pedimos, haya llegado a empezar o
        # no (en la caja algunos se atascan en 00:00). La película que ponga tu padre nunca lleva esa clave.
        return (self.expect is not None and bool(self.key) and self.player.is_playing()
                and self.key in self.player.playing_file())

    def _pending(self):
        # Pedido a YouTube pero sin empezar todavía (unos segundos, con el "Cargando…" de Kodi en pantalla).
        return self.expect is not None and self.player.started_count() < self.expect

    def _stop_ours(self):
        if self._pending() and not self._ours():
            self.cancel = True  # olvidarlo ahora lo dejaría sonando (o congelado) sin que nadie lo pare
            return
        if not self._ours():
            self.expect = None
        elif not self.cond('Window.IsActive(fullscreenvideo)'):
            self.player.stop()
            self.expect = None
        # A pantalla completa lo está viendo tu padre: no se le quita, pero se sigue vigilando por si se atasca.

    def _check_stall(self):
        if not self._ours():
            return
        duration, position = self.player.duration(), self.player.position()
        if self.watch.failures() >= STALL_FAILS or (duration and position > duration + OVERRUN):
            # Aunque esté a pantalla completa: una imagen congelada nunca es lo que tu padre quiere ver.
            self.player.stop()
            self._give_up()
        elif position >= GOOD_AFTER:
            self.streak = 0

    def _give_up(self):
        self.expect, self.cancel, self.opening = None, False, False
        self.stalled.add(self.key)
        self.streak += 1
        self.gave_up_at = self.clock()

    def _paused(self, now):
        if self.streak >= MAX_STALLS and now - self.gave_up_at >= PAUSE:
            self.streak = 0  # pasada la pausa, se vuelve a probar
        return self.streak >= MAX_STALLS

    def _check_failed_open(self, now):
        if self._pending():
            if self.player.is_playing():
                self.opening = True
            elif self.opening:
                # Kodi lo estaba abriendo y lo cerró sin empezar. Un aviso cualquiera mientras YouTube aún prepara
                # el vídeo no cuenta: puede ser de Palantir o de BlackGhost y tu padre tiene que leerlo.
                self._give_up()
                self.failed_at = now
        if self.failed_at is not None:
            if now - self.failed_at > ERROR_WINDOW:
                self.failed_at = None
            elif self.cond('Window.IsVisible(okdialog)'):
                self.close_error()  # su "Error de reproducción" no le dice nada a tu padre
                self.failed_at = None

    def _update_dim(self):
        want = self._ours() and self.player.position() >= DIM_AFTER
        if want != self.dimmed:
            self.dimmed = want
            self.dim(want)

    def tick(self):
        focus, now = self._focus(), self.clock()
        # Lo pedido no se olvida nunca, aunque YouTube tarde minutos (la clave impide confundirlo con otra cosa):
        # si se abre tarde y el foco sigue ahí, se vigila; si el foco se fue, se para en cuanto se abra.
        self._check_failed_open(now)
        if self.cancel and self._ours():
            self.player.stop()
            self.expect, self.cancel = None, False
        self._check_stall()
        self._update_dim()
        if focus is None and self._pending():
            return  # el "Cargando…" de Kodi mientras YouTube prepara el vídeo no es un cambio de foco
        if focus != self.focus:
            self.focus, self.since, self.done_for = focus, now, None
            self._stop_ours()
            return
        if focus is None or self.done_for == focus or now - self.since < self.delay:
            return
        self.done_for = focus
        if (not self.enabled() or self._paused(now) or self.player.is_playing()
                or self.cond('Window.IsActive(fullscreenvideo)')):
            return
        key = self.resolve(*focus)
        if not key or key in self.stalled or self._focus() != focus:
            return
        before = self.player.started_count()
        self.watch.mark()
        self.player.play(youtube_url(key))
        self.expect, self.key, self.cancel, self.opening = before + 1, key, False, False
