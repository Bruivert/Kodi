# -*- coding: utf-8 -*-
"""Servicio de fondo: termina de montar el menú tras el cambio de skin y pone los
tráileres automáticos de España."""
import json
import time

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import kodi_setup as ks
from resources.lib import patches, trailers
from resources.lib.trailer_service import LogWatch, TrailerAutoplay


class PapaPlayer(xbmc.Player):
    def __init__(self):
        super(PapaPlayer, self).__init__()
        self.count = 0

    def onAVStarted(self):
        self.count += 1


class PlayerAdapter(object):
    def __init__(self, player):
        self.player = player

    def play(self, url):
        self.player.play(url, windowed=True)

    def stop(self):
        self.player.stop()

    def is_playing(self):
        return self.player.isPlaying()

    def started_count(self):
        return self.player.count

    def position(self):
        try:
            return self.player.getTime()
        except RuntimeError:  # ya no hay nada reproduciéndose
            return 0.0

    def duration(self):
        try:
            return self.player.getTotalTime()
        except RuntimeError:
            return 0.0

    def playing_file(self):
        try:
            return self.player.getPlayingFile()  # p. ej. …/youtube/manifest/dash?file=<vídeo>.mpd
        except RuntimeError:
            return ''


def dim_rows(on):
    # La skin, con el arreglo de patches.py, atenúa las filas de carátulas mientras esta propiedad vale 1.
    home = xbmcgui.Window(10000)
    if on:
        home.setProperty(patches.TRAILER_PROPERTY, '1')
    else:
        home.clearProperty(patches.TRAILER_PROPERTY)


HEADERS = {'Accept': 'application/json', 'User-Agent': 'KodiPapa/1.0'}


def http_get(url):
    # requests trae sus certificados (certifi): el Python de Kodi en Android a veces no tiene los del sistema.
    # Se importa aquí para que, si faltara, solo se pierdan los tráileres y no el resto del servicio.
    try:
        import requests
    except ImportError:
        requests = None
    if requests is not None:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        return response.json()
    from urllib.request import Request, urlopen
    with urlopen(Request(url, headers=HEADERS), timeout=5) as response:
        return json.loads(response.read().decode('utf-8'))


class Resolver(object):
    def __init__(self):
        self.cache = {}

    def __call__(self, kind, tmdb_id, imdb_id, title, year):
        api_key = ks.setting('tmdb_key')
        if not api_key or not ks.has_addon(ks.YOUTUBE):
            return None
        cache_key = (kind, tmdb_id, imdb_id, title, year)
        if cache_key in self.cache:
            return self.cache[cache_key]
        failed = []

        def get(url):
            try:
                return http_get(url)
            except Exception:
                failed.append(url)
                raise

        tid = trailers.resolve_tmdb_id(kind, tmdb_id, imdb_id, title, year, api_key, get)
        key = trailers.spain_trailer(kind, tid, api_key, get) if tid else None
        if not failed:  # un fallo de red no es "no tiene tráiler": se vuelve a preguntar la próxima vez
            if len(self.cache) > 500:
                self.cache.clear()
            self.cache[cache_key] = key
        return key


def main():
    monitor = xbmc.Monitor()
    try:  # tras actualizarse YouTube o la skin, se vuelven a aplicar los arreglos (la skin, al siguiente arranque)
        ks.apply_patches()
    except Exception as exc:
        ks.log('arreglos: %s' % exc)
    dim_rows(False)
    autoplay = TrailerAutoplay(xbmc.getInfoLabel, xbmc.getCondVisibility, PlayerAdapter(PapaPlayer()),
                               Resolver(), lambda: ks.setting('trailers_auto') != 'false', time.time,
                               watch=LogWatch(xbmcvfs.translatePath('special://logpath/kodi.log')),
                               close_error=lambda: xbmc.executebuiltin('Dialog.Close(okdialog)'), dim=dim_rows)
    last_check = 0.0
    fallos = 0  # cada intento recarga la skin: no insistir sin fin
    while not monitor.abortRequested():
        now = time.time()
        if now - last_check > 3:
            last_check = now
            if fallos < 3 and ks.finish_pending(lambda: monitor.waitForAbort(3)) is False:
                fallos += 1
                ks.log('el menú no se copió (intento %d)' % fallos)
                if fallos == 3:
                    ks.notify('No se pudo montar el menú. Reinicia Kodi.', 8000)
        try:
            autoplay.tick()
        except Exception as exc:  # un fallo de red o de un tráiler no debe tumbar el servicio
            ks.log('tráiler: %s' % exc)
        if monitor.waitForAbort(0.5):
            break


if __name__ == '__main__':
    main()
