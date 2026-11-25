# -*- coding: utf-8 -*-
"""Ver los torrents por AllDebrid en vez de con Elementum.

Los torrents en 1080p/4K de las webs en castellano tienen poca gente compartiéndolos y Elementum se quedaba parado
(23/11/2026). AllDebrid los descarga en sus servidores y da un enlace directo: los que ya tiene arrancan en segundos.
Balandro no usa debrid (lo dice su ayuda), así que el asistente coge el .torrent de la página de la web, saca su
identificador (btih) y se lo pasa a AllDebrid por ResolveURL, donde está la cuenta vinculada. Puro.
"""
import hashlib
from urllib import parse

from resources.lib import calidad


def _bdecode(data, i):
    """Un valor bencode desde i: (valor, fin). Los diccionarios guardan (valor, inicio, fin) por clave, para poder
    calcular el hash del diccionario «info» tal como viene."""
    c = data[i:i + 1]
    if c == b'i':
        end = data.index(b'e', i)
        return int(data[i + 1:end]), end + 1
    if c == b'l':
        i, out = i + 1, []
        while data[i:i + 1] != b'e':
            value, i = _bdecode(data, i)
            out.append(value)
        return out, i + 1
    if c == b'd':
        i, out = i + 1, {}
        while data[i:i + 1] != b'e':
            key, i = _bdecode(data, i)
            start = i
            value, i = _bdecode(data, i)
            out[key] = (value, start, i)
        return out, i + 1
    colon = data.index(b':', i)
    size = int(data[i:colon])
    return data[colon + 1:colon + 1 + size], colon + 1 + size


def info_hash(torrent):
    """El btih (sha1 del diccionario «info») de un .torrent, o None si no lo es."""
    try:
        top, _ = _bdecode(torrent, 0)
        _, start, end = top[b'info']
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    return hashlib.sha1(torrent[start:end]).hexdigest()


def magnet(btih, name=''):
    return 'magnet:?xt=urn:btih:%s' % btih + ('&dn=%s' % parse.quote(name) if name else '')


def _rank(quality):
    q = (quality or '').lower()
    return 0 if '1080' in q or 'full' in q else 1  # 1080p primero (menos peso para la caja); luego 4K


def hd_links(links):
    """Los torrents de 1080p o más de una página ([(calidad, url)]), los de 1080p primero."""
    return [url for q, url in sorted((l for l in links or [] if calidad.is_hd(l[0])), key=lambda l: _rank(l[0]))]


def pow_nonce(challenge, difficulty=3):
    """La respuesta al reto de DonTorrent (api_validate_pow.php): el primer número que, pegado al reto, da un sha256
    que empieza por difficulty ceros. Como nonce_gen de Balandro (channels/dontorrents.py)."""
    target, nonce = '0' * difficulty, 0
    while not hashlib.sha256((challenge + str(nonce)).encode()).hexdigest().startswith(target):
        nonce += 1
    return nonce
