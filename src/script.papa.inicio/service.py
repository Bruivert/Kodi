# -*- coding: utf-8 -*-
"""Servicio de fondo: termina de montar el menú tras el cambio de skin y pone los
tráileres automáticos de España."""
import json
import time

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import kodi_setup as ks
from resources.lib import arte_deportes, catalogo, filas, fondo, historial, patches, pegar, trailers
from resources.lib.trailer_service import LogWatch, TrailerAutoplay


class PapaPlayer(xbmc.Player):
    def __init__(self):
        super(PapaPlayer, self).__init__()
        self.count = 0
        self.on_started = None  # historial.Tracker.started: ¿arrancó la fuente que eligió el asistente?

    def onAVStarted(self):
        self.count += 1
        if self.on_started:
            try:
                self.on_started()
            except Exception as exc:
                ks.log('historial: %s' % exc)


def take_pending():
    """Lo que dejó apuntado plugin.py al pulsar (y se borra), o None."""
    home = xbmcgui.Window(10000)
    raw = home.getProperty(historial.PENDING)
    home.clearProperty(historial.PENDING)
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


def _load_json(path):
    try:
        return json.loads(ks.read_file(path) or '{}')
    except ValueError:
        return {}


def mark_ok(playing):
    """La fuente arrancó: la próxima vez se vuelve a usar (balandro.pick)."""
    intentos = _load_json(ks.INTENTOS)
    entry = intentos.get(historial.key(playing))
    if entry and entry.get('fuente') == playing.get('fuente'):
        entry['ok'] = True
        ks.write_file(ks.INTENTOS, json.dumps(intentos))


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
    player = PapaPlayer()
    # Si la fuente elegida al pulsar arranca, se da por buena; si no, el siguiente intento usa otra (historial.py).
    player.on_started = historial.Tracker(take_pending, mark_ok, time.time).started
    autoplay = TrailerAutoplay(xbmc.getInfoLabel, xbmc.getCondVisibility, PlayerAdapter(player),
                               Resolver(), lambda: ks.setting('trailers_auto') != 'false', time.time,
                               watch=LogWatch(xbmcvfs.translatePath('special://logpath/kodi.log')),
                               close_error=lambda: xbmc.executebuiltin('Dialog.Close(okdialog)'), dim=dim_rows)
    # Tras actualizarse YouTube o la skin (también con Kodi encendido) se vuelven a aplicar los arreglos.
    keeper = patches.PatchKeeper(ks.apply_patches, xbmc.getCondVisibility, reload_skin, time.time, ks.SKIN)
    # Copias de las filas de Palantir: se renuevan de una en una cuando nadie usa el mando ni ve una película.
    refresher = filas.Refresher(lambda: filas.row_paths(ks.load_rutas()), ks.load_fila_index, ks.fetch_row_hd,
                                ks.save_fila, lambda: xbmc.getCondVisibility(
                                    'System.IdleTime(20) + !Window.IsActive(fullscreenvideo)'), time.time)
    # Fondos de Deportes: de TheSportsDB, una petición por minuto como mucho (su clave gratuita deja muy pocas).
    arte = arte_deportes.Fetcher(ks.load_arte, ks.save_arte, http_get, lambda: xbmc.getCondVisibility(
        '!Window.IsActive(fullscreenvideo)'), time.time)
    # Calidad (1080p o más) de los títulos de las filas de Balandro guardadas, poco a poco y con la caja tranquila.
    calidades = fondo.Every(ks.check_saved_rows, 30, lambda: xbmc.getCondVisibility('!Window.IsActive(fullscreenvideo)'),
                            time.time)
    # De madrugada, una vez al día y con la caja sin usar: lo nuevo del grupo de Telegram al catálogo y lo de las filas
    # preparado en AllDebrid (precalentar.py).
    telegram_job = fondo.Every(ks.nightly, 1800, lambda: xbmc.getCondVisibility(
        'System.IdleTime(600) + !Player.HasMedia'), time.time)
    # Índice de títulos de Palantir para la lupa, listo antes de la primera búsqueda.
    indice = catalogo.IndexKeeper(ks.palantir_db, xbmcvfs.translatePath(ks.CATALOGO), time.time)
    # En un hilo aparte: cada petición tarda segundos y aquí dejaba a los tráileres sin responder al mando.
    worker = fondo.Worker([('fila pedida', refresher.tick), ('fondo de deportes pedido a TheSportsDB', arte.tick),
                           ('lupa', indice.tick), ('calidad', calidades.tick), ('de madrugada', telegram_job.tick)],
                          monitor.waitForAbort, ks.log)
    worker.start()
    try:  # página para pegar desde el móvil la dirección de PeLiS (pegar.py)
        pagina = pegar.serve(lambda: ks.setting(pegar.SETTING), lambda url: ks.set_setting(pegar.SETTING, url))
    except Exception as exc:
        pagina = None
        ks.log('página de PeLiS: %s' % exc)
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
    if pagina:
        pagina.shutdown()
    worker.join(10)


if __name__ == '__main__':
    main()
