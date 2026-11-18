# -*- coding: utf-8 -*-
"""Servicio de fondo: termina de montar el menú tras el cambio de skin y pone los
tráileres automáticos de España."""
import json
import time

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import kodi_setup as ks
from resources.lib import arte_deportes, filas, fondo, patches, trailers
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
        ks.log('tráiler: se pide %s' % url.rsplit('=', 1)[-1])
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


def reload_skin():
    ks.log('skin recargada para que vuelva el fundido de las filas')
    xbmc.executebuiltin('ReloadSkin()')


HEADERS = {'Accept': 'application/json', 'User-Agent': 'KodiPapa/1.0'}


def http_get(url, payload=None):
    # requests trae sus certificados (certifi): el Python de Kodi en Android a veces no tiene los del sistema.
    # Se importa aquí para que, si faltara, solo se pierdan los tráileres y no el resto del servicio.
    try:
        import requests
    except ImportError:
        requests = None
    if requests is not None:
        if payload is None:
            response = requests.get(url, headers=HEADERS, timeout=5)
        else:
            response = requests.post(url, json=payload, headers=HEADERS, timeout=5)
        response.raise_for_status()
        return response.json()
    from urllib.request import Request, urlopen
    data, headers = None, HEADERS
    if payload is not None:
        data, headers = json.dumps(payload).encode('utf-8'), dict(HEADERS, **{'Content-Type': 'application/json'})
    with urlopen(Request(url, data=data, headers=headers), timeout=5) as response:
        return json.loads(response.read().decode('utf-8'))


def http_post(url, payload):
    return http_get(url, payload)


class PapaMonitor(xbmc.Monitor):
    """Avisa cuando cambian los ajustes del asistente (p. ej. un código nuevo de BlackGhost)."""

    def __init__(self):
        super(PapaMonitor, self).__init__()
        self.settings_changed = False

    def onSettingsChanged(self):
        self.settings_changed = True


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

        def noting_failures(request):
            def call(url, *payload):
                try:
                    return request(url, *payload)
                except Exception:
                    failed.append(url)
                    raise
            return call
        get, post = noting_failures(http_get), noting_failures(http_post)

        started = time.time()
        tid = trailers.resolve_tmdb_id(kind, tmdb_id, imdb_id, title, year, api_key, get)
        key = trailers.find_trailer(kind, tid, api_key, get, post) if tid else None
        ks.log('tráiler: buscado en %.1f s → %s' % (time.time() - started,
                                                    key or ('fallo de red' if failed else 'sin tráiler')))
        if not failed:  # un fallo de red no es "no tiene tráiler": se vuelve a preguntar la próxima vez
            if len(self.cache) > 500:
                self.cache.clear()
            self.cache[cache_key] = key
        return key


def main():
    monitor = PapaMonitor()
    try:
        ks.apply_youtube_settings()
        ks.refresh_menu_if_outdated()
        ks.sync_bg_code()
    except Exception as exc:
        ks.log('arreglos: %s' % exc)
    dim_rows(False)
    autoplay = TrailerAutoplay(xbmc.getInfoLabel, xbmc.getCondVisibility, PlayerAdapter(PapaPlayer()),
                               Resolver(), lambda: ks.setting('trailers_auto') != 'false', time.time,
                               watch=LogWatch(xbmcvfs.translatePath('special://logpath/kodi.log')),
                               close_error=lambda: xbmc.executebuiltin('Dialog.Close(okdialog)'), dim=dim_rows)
    # Tras actualizarse YouTube o la skin (también con Kodi encendido) se vuelven a aplicar los arreglos.
    keeper = patches.PatchKeeper(ks.apply_patches, xbmc.getCondVisibility, reload_skin, time.time, ks.SKIN)
    # Copias de las filas de Palantir: se renuevan de una en una cuando nadie usa el mando ni ve una película.
    refresher = filas.Refresher(lambda: filas.row_paths(ks.load_rutas()), ks.load_fila_index, ks.fetch_row,
                                ks.save_fila, lambda: xbmc.getCondVisibility(
                                    'System.IdleTime(20) + !Window.IsActive(fullscreenvideo)'), time.time)
    # Fondos de Deportes: de TheSportsDB, una petición por minuto como mucho (su clave gratuita deja muy pocas).
    arte = arte_deportes.Fetcher(ks.load_arte, ks.save_arte, http_get, lambda: xbmc.getCondVisibility(
        '!Window.IsActive(fullscreenvideo)'), time.time)
    # En un hilo aparte: cada petición tarda segundos y aquí dejaba a los tráileres sin responder al mando.
    worker = fondo.Worker([('fila pedida', refresher.tick), ('fondo de deportes pedido a TheSportsDB', arte.tick)],
                          monitor.waitForAbort, ks.log)
    worker.start()
    last_check = 0.0
    fallos = 0  # cada intento recarga la skin: no insistir sin fin
    while not monitor.abortRequested():
        now = time.time()
        if now - last_check > 3:
            last_check = now
            if monitor.settings_changed:
                monitor.settings_changed = False
                try:
                    ks.sync_bg_code()
                except Exception as exc:
                    ks.log('BlackGhost: %s' % exc)
            if fallos < 3 and ks.finish_pending(lambda: monitor.waitForAbort(3)) is False:
                fallos += 1
                ks.log('el menú no se copió (intento %d)' % fallos)
                if fallos == 3:
                    ks.notify('No se pudo montar el menú. Reinicia Kodi.', 8000)
        try:
            keeper.tick()
        except Exception as exc:
            ks.log('arreglos: %s' % exc)
        try:
            autoplay.tick()
        except Exception as exc:  # un fallo de red o de un tráiler no debe tumbar el servicio
            ks.log('tráiler: %s' % exc)
        if monitor.waitForAbort(0.5):
            break
    worker.join(10)


if __name__ == '__main__':
    main()
