# -*- coding: utf-8 -*-
"""Tráiler automático de fondo, como en Netflix: si el foco se queda quieto unos segundos
en una película o serie de los menús, suena su tráiler de España en segundo plano.

Todo llega inyectado (infolabels, condiciones, reproductor, reloj) para poder probarlo
sin Kodi; service.py conecta las piezas reales."""
from resources.lib.trailers import youtube_url

WINDOWS = ('home', '1101', '1102', '1103', '1104', '1109')
KINDS = {'movie': 'movie', 'tvshow': 'tv'}
DELAY = 4.0


class TrailerAutoplay(object):
    def __init__(self, info, cond, player, resolve, enabled, clock, delay=DELAY):
        self.info, self.cond, self.player = info, cond, player
        self.resolve, self.enabled, self.clock, self.delay = resolve, enabled, clock, delay
        self.focus = None
        self.since = 0.0
        self.done_for = None
        self.expect = None  # nº de reproducciones que habrá cuando empiece nuestro tráiler

    def _focus(self):
        if not any(self.cond('Window.IsActive(%s)' % w) for w in WINDOWS):
            return None
        kind = KINDS.get(self.info('ListItem.DBType'))
        if not kind:
            return None
        return (kind, self.info('ListItem.UniqueID(tmdb)'), self.info('ListItem.IMDBNumber'),
                self.info('ListItem.Title') or self.info('ListItem.Label'), self.info('ListItem.Year'))

    def _ours(self):
        return (self.expect is not None and self.player.is_playing()
                and self.player.started_count() == self.expect)

    def _stop_ours(self):
        # Solo paramos nuestro tráiler; nunca lo que tu padre haya puesto ni lo que va a pantalla completa.
        if self._ours() and not self.cond('Window.IsActive(fullscreenvideo)'):
            self.player.stop()
        self.expect = None

    def tick(self):
        focus, now = self._focus(), self.clock()
        if focus != self.focus:
            self.focus, self.since, self.done_for = focus, now, None
            self._stop_ours()
            return
        if focus is None or self.done_for == focus or now - self.since < self.delay:
            return
        self.done_for = focus
        if not self.enabled() or self.player.is_playing() or self.cond('Window.IsActive(fullscreenvideo)'):
            return
        key = self.resolve(*focus)
        if not key or self._focus() != focus:
            return
        before = self.player.started_count()
        self.player.play(youtube_url(key))
        self.expect = before + 1
