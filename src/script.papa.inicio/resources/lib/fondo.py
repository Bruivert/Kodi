# -*- coding: utf-8 -*-
"""Trabajo de fondo del servicio en un hilo aparte: renovar las copias de las filas y bajar los fondos de Deportes.

Cada petición (Palantir, BlackGhost, TheSportsDB) tarda de 3 a 30 s. En el bucle del servicio dejaba sin respuesta a
los tráileres: si se movía el foco mientras tanto, el tráiler seguía sonando y las filas atenuadas.
"""
import threading


class Worker(threading.Thread):
    """jobs: [(nombre, tick)]; tick() devuelve lo que ha hecho (para el log) o None. wait(s) devuelve True cuando Kodi
    se cierra (xbmc.Monitor().waitForAbort)."""

    def __init__(self, jobs, wait, log):
        super(Worker, self).__init__(name='papa-fondo')
        self.daemon = True  # no impide que Kodi se cierre
        self.jobs, self.wait, self.log = jobs, wait, log

    def run(self):
        while not self.wait(1.0):
            for name, tick in self.jobs:
                try:
                    done = tick()
                    if done:
                        self.log('%s: %s' % (name, done))
                except Exception as exc:  # un fallo de red no debe parar el hilo
                    self.log('%s: %s' % (name, exc))
