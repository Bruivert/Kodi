# -*- coding: utf-8 -*-
"""La lupa busca en Palantir, como "Buscar: Por título": teclado, películas o series, y la lista de Palantir para
elegir y ver. El código de Palantir está ofuscado y su búsqueda no se puede pedir con el texto en la dirección (por
JSON-RPC devuelve error): se abre en la interfaz y se le escribe el texto en su teclado.

Palantir, cuando una búsqueda da resultados, pone la propiedad p3_play en la ventana de Inicio para que, al volver a
esa lista (Atrás desde una serie, o al acabar de ver algo), la repita sin preguntar; solo la quita al abrir uno de sus
menús. Abierta desde la lupa repetiría la última búsqueda (aunque fuera de películas y ahora se pidan series): se
quita antes de abrirla. Puro: Kodi llega inyectado.
"""
WAIT = 20.0  # s: Palantir tarda de 3,5 a 9 s en sacar su teclado en la caja
STEP = 0.25
KINDS = (('peliculas', 'Películas'), ('series', 'Series'))
REPEAT_PROPERTY = 'p3_play'  # la de Palantir (libs/ioOOo000OOO, buscar3)
RESULT_WAIT = 600.0  # s: el aviso de Palantir de "sin resultados" espera a que lo acepten
BUSY = 'System.HasActiveModalDialog | Window.IsActive(busydialog) | Window.IsActive(busydialognocancel)'


def choices(rutas):
    """[(clave, etiqueta, ruta de "Por título")] de lo que Palantir tiene."""
    found = ((rutas or {}).get('palantir') or {}).get('buscar') or {}
    return [(key, label, found[key]) for key, label in KINDS if found.get(key)]


def open_commands(path):
    """Quitar la marca de "repetir la última búsqueda" de Palantir y abrir la suya."""
    return 'ClearProperty(%s,10000)' % REPEAT_PROPERTY, 'ActivateWindow(videos,"%s",return)' % path


def wait_for(check, sleep, limit=WAIT, step=STEP):
    """Lo primero que devuelva check() que no sea None, mirando cada step s; None si se pasa el límite."""
    waited = 0.0
    while waited < limit:
        got = check()
        if got is not None:
            return got
        sleep(step)
        waited += step
    return None


def autofill(is_open, send, sleep, text):
    """Espera a que salga el teclado de Palantir y le escribe el texto (y acepta). False si no llega a salir."""
    if not wait_for(lambda: True if is_open() else None, sleep):
        return False
    sleep(0.4)  # que termine de abrirse
    send(text)
    return True


def after_search(videos_active, busy, folder_path, num_items, path):
    """Cómo ha acabado la búsqueda: 'ok' (la lista de Palantir), 'empty' (Palantir no encontró nada, lo avisó y Kodi
    se quedó en su biblioteca de vídeo: "Archivos, Listas de reproducción…"), 'away' (se fue a otra pantalla) o
    None (cargando, o con el aviso de Palantir aún abierto)."""
    if busy:
        return None
    if not videos_active:
        return 'away'
    if folder_path.rstrip('/') == path.rstrip('/'):
        return 'ok' if (num_items or '0') != '0' else None
    return 'empty'
