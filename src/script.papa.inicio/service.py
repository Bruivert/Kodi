# -*- coding: utf-8 -*-
"""Servicio de fondo: termina de montar el menú tras el cambio de skin y pone los
tráileres automáticos de España."""
import json
import time

import xbmc

from resources.lib import kodi_setup as ks
from resources.lib import trailers
from resources.lib.trailer_service import TrailerAutoplay


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
        if cache_key not in self.cache:
            if len(self.cache) > 500:
                self.cache.clear()
            tid = trailers.resolve_tmdb_id(kind, tmdb_id, imdb_id, title, year, api_key, http_get)
            self.cache[cache_key] = trailers.spain_trailer(kind, tid, api_key, http_get) if tid else None
        return self.cache[cache_key]


def main():
    monitor = xbmc.Monitor()
    autoplay = TrailerAutoplay(xbmc.getInfoLabel, xbmc.getCondVisibility, PlayerAdapter(PapaPlayer()),
                               Resolver(), lambda: ks.setting('trailers_auto') != 'false', time.time)
    last_check = 0.0
    while not monitor.abortRequested():
        now = time.time()
        if now - last_check > 3:
            last_check = now
            if ks.pending() and ks.af3_ready() and xbmc.getCondVisibility('Window.IsVisible(home)'):
                if monitor.waitForAbort(3):  # deja que la skin termine de arrancar
                    break
                ks.apply_skin_config()
                ks.set_pending(False)
                ks.notify('Menú de papá listo')
        try:
            autoplay.tick()
        except Exception as exc:  # un fallo de red o de un tráiler no debe tumbar el servicio
            ks.log('tráiler: %s' % exc)
        if monitor.waitForAbort(0.5):
            break


if __name__ == '__main__':
    main()
