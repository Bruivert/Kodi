# -*- coding: utf-8 -*-
"""Los enlaces del catálogo de Palantir, vistos con la cuenta de AllDebrid de la caja, sin el addon de Palantir.

Palantir cerró el 17/11/2026, pero su catálogo sigue en la caja (base SQLite, congelada al 12/11) y sus enlaces no
dependían de él: son ficheros de 1fichier, en 1080p/4K y castellano casi siempre, que Palantir desbloqueaba con la
cuenta de AllDebrid vinculada en la caja (sus ajustes: Alldebrid_enabled). Están cifrados con AES-OFB y una clave fija
(Resolver.__init__ de sus libs). Aquí se descifran y se elige el mejor; plugin.py lo desbloquea con AllDebrid
(ResolveURL). Así se ve lo del catálogo al momento aunque el addon de Palantir se rompa. Puro salvo pyaes.
"""
import base64

from resources.lib import calidad

_SECRET = base64.b64decode(b'hTh8uRnL5bX8PZC6Tc3t46nVDFfBpB6Tjw3qazQThpexpg8bLdimevNHj5vJR0nP')
KEY, IV = _SECRET[16:], _SECRET[:16]


def _aes():
    try:
        import pyaes  # script.module.pyaes (la instaló Alfa); en Python puro, como pide Kodi en Android
    except ImportError:  # Kodi aún no ha leído la dependencia del addon.xml (se lee al arrancar)
        import sys
        import xbmcvfs
        sys.path.append(xbmcvfs.translatePath('special://home/addons/script.module.pyaes/lib'))
        import pyaes
    return pyaes.AESModeOfOperationOFB(KEY, iv=IV)


def decrypt(link):
    """La dirección de un enlace del catálogo ('https://1fichier.com/?…'), o '' si no se puede."""
    if not link:
        return ''
    if link.startswith('http'):
        return link
    try:
        data = base64.urlsafe_b64decode(link + '=' * (-len(link) % 4))
        url = _aes().decrypt(data).decode('utf-8')
    except Exception:
        return ''
    return url if url.startswith('http') else ''


def encrypt(url):
    """Lo contrario de decrypt (para las pruebas)."""
    return base64.urlsafe_b64encode(_aes().encrypt(url.encode('utf-8'))).decode('ascii').rstrip('=')


def _rank(quality):
    """1080p primero (menos peso para la caja y para la red); luego 4K; Dolby Vision al final (no todas las teles)."""
    q = (quality or '').lower()
    if 'dv' in q:
        return 3
    if '4k' in q or '2160' in q:
        return 2 if 'hdr' in q else 1
    return 0


def _hd(quality):
    q = (quality or '').lower()
    return calidad.is_hd(q) or 'dv' in q or 'hdr' in q


def best(links):
    """Los enlaces que valen ([{link, calidad, audio}]), en el orden en que probarlos: con castellano y de 1080p o
    más, 1080p primero. Los «(R)» (versiones recomprimidas) van detrás de los demás de su calidad."""
    good = [l for l in links or [] if 'esp' in (l.get('audio') or '').lower() and _hd(l.get('calidad'))]
    return sorted(good, key=lambda l: (_rank(l.get('calidad')), '(r)' in (l.get('calidad') or '').lower()))
