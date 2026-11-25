# -*- coding: utf-8 -*-
"""Página para pegar desde el móvil la dirección personal de PeLiS (http://<caja>:8770).

La dirección de PeLiS lleva cifrada la clave de AllDebrid del usuario: no debe pasar por el chat ni teclearse con el
mando. El servicio sirve esta página en la red de casa; se pega, se comprueba que es de pelis-addon.com y se guarda
en un ajuste oculto del asistente. Nunca se vuelve a enseñar, solo si hay una guardada. Puro salvo el servidor.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

PORT = 8770
SETTING = 'pelis_url'
HOST = 'https://pelis-addon.com/'

_PAGE = '''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Kodi de Papá · PeLiS</title>
<style>body{font-family:-apple-system,sans-serif;margin:24px;max-width:560px;line-height:1.5}
textarea{width:100%%;height:110px;font-size:15px;box-sizing:border-box}button{font-size:17px;padding:10px 18px;margin-top:10px}
.ok{color:#1a7f37}.err{color:#b42318}.note{color:#555;font-size:14px}</style></head><body>
<h2>Dirección de PeLiS</h2>
<p>Pega aquí la dirección que te da <b>pelis-addon.com/configure</b> al pulsar «Generar addon».</p>
%s
<form method="post"><textarea name="url" placeholder="https://pelis-addon.com/..." autocomplete="off"
autocapitalize="off" spellcheck="false"></textarea><br><button type="submit">Guardar en la caja</button></form>
<p class="note">%s La dirección lleva tu clave de AllDebrid cifrada: no se vuelve a mostrar.</p></body></html>'''


def clean(text):
    """La dirección pegada, sin espacios ni «/manifest.json» al final, o None si no es de PeLiS."""
    url = ''.join((text or '').split())
    if url.startswith('stremio://'):
        url = 'https://' + url[len('stremio://'):]
    if not url.startswith(HOST) or len(url) <= len(HOST):
        return None
    for tail in ('/manifest.json', '/configure', '/'):
        if url.endswith(tail):
            url = url[:-len(tail)]
    return url


def page(message='', saved=False):
    status = 'Ya hay una dirección guardada; si pegas otra, la sustituye.' if saved else 'Aún no hay ninguna guardada.'
    return _PAGE % (message, status)


def _handler(load, save):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, code=200):
            data = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(page(saved=bool(load())))

        def do_POST(self):
            size = min(int(self.headers.get('Content-Length') or 0), 8192)
            text = parse_qs(self.rfile.read(size).decode('utf-8', 'ignore')).get('url', [''])[0]
            url = clean(text)
            if not url:
                self._send(page('<p class="err">Eso no parece una dirección de pelis-addon.com.</p>', bool(load())), 400)
                return
            save(url)
            self._send(page('<p class="ok"><b>Guardada.</b> Ya puedes cerrar esta página.</p>', True))

        def log_message(self, *args):  # nada en el log de Kodi: la dirección no debe quedar escrita
            pass
    return Handler


def serve(load, save, port=PORT):
    """Arranca la página en un hilo y devuelve el servidor (server.shutdown() para pararla)."""
    server = HTTPServer(('0.0.0.0', port), _handler(load, save))
    threading.Thread(target=server.serve_forever, name='papa-pegar', daemon=True).start()
    return server
