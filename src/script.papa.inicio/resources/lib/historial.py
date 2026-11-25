# -*- coding: utf-8 -*-
"""Saber si la fuente elegida al pulsar llegó a arrancar.

Al pulsar algo, plugin.py apunta la fuente que prueba (intentos.json, ok=False) y deja en una propiedad de la ventana
de Inicio qué va a sonar (PENDING). Cuando empieza el vídeo, el servicio la recoge (Tracker.started) y da la fuente por
buena; si no empieza, el siguiente intento de esa ficha usa otra fuente (balandro.pick). Los tráileres y lo que no
lanza el asistente no dejan nada apuntado. Puro: lo apuntado, el aviso y el reloj llegan de fuera.
"""
PENDING = 'papa.reproduciendo'  # propiedad de la ventana 10000 con el JSON de lo que se va a reproducir
PENDING_MAX = 300  # s: lo apuntado al pulsar vale si el vídeo empieza antes (Elementum tarda ~20 s en arrancar)


def key(entry):
    if entry.get('kind') == 'series':
        return 'series:%s:%s:%s' % (entry['tmdb'], entry.get('season'), entry.get('episode'))
    return 'peliculas:%s' % entry['tmdb']


class Tracker(object):
    """Lo usa el servicio. pending() da lo apuntado al pulsar (dict o None) y lo borra; mark_ok(playing) da por
    buena su fuente."""

    def __init__(self, pending, mark_ok, clock):
        self.pending, self.mark_ok, self.clock = pending, mark_ok, clock

    def started(self):
        """Empezó un vídeo (onAVStarted). Si lo lanzó el asistente hace poco, su fuente funciona."""
        playing = self.pending()
        if not playing or self.clock() - playing.get('time', 0) > PENDING_MAX:
            return None
        self.mark_ok(playing)
        return playing
