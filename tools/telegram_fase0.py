# -*- coding: utf-8 -*-
"""Fase 0 del grupo de Telegram: ¿sirve como biblioteca tipo Palantir?  venv/bin/python tools/telegram_fase0.py

Solo mide, no cambia nada en Telegram ni en la caja. Lee las credenciales de ~/.config/kodi-papa/telegram.env (api_id,
api_hash, grupo) y nunca las escribe en pantalla. El inicio de sesión es con QR: en el móvil, Telegram → Ajustes →
Dispositivos → Vincular dispositivo, y se escanea el código que se abre en una ventana. Si la cuenta tiene verificación
en dos pasos, la contraseña se teclea aquí (no se ve ni se guarda). La sesión queda en ~/.config/kodi-papa (600).

Cuenta los vídeos, sus resoluciones (por ancho × alto), cuántos nombres se entienden (título, año, temporada y
capítulo) y la velocidad de descarga de 30 MB de un vídeo de 1080p. Deja el informe en ~/.config/kodi-papa/fase0.json.
"""
import getpass
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter

CONFIG = os.path.expanduser('~/.config/kodi-papa')
ENV = os.path.join(CONFIG, 'telegram.env')
SESSION = os.path.join(CONFIG, 'telegram')
REPORT = os.path.join(CONFIG, 'fase0.json')
VIDEOS = os.path.join(CONFIG, 'fase0_videos.json')  # la lista entera, para no volver a leer el grupo
QR_PNG = os.path.join(CONFIG, 'qr.png')
SAMPLE_MB = 30

_EPISODE = re.compile(r'\bS(\d{1,2})\s*E(\d{1,3})\b|\b(\d{1,2})x(\d{1,3})\b|\bCap[a-zí.]*\s*(\d{1,2})(\d{2})\b', re.I)
_YEAR = re.compile(r'[(\[\s._-]((?:19|20)\d{2})(?:[)\]\s._-]|$)')
_JUNK = re.compile(r'[\[(]?\b(?:1080p?|2160p?|720p?|4k|uhd|hdr\d*|bluray|blu-ray|web-?dl|webrip|hdtv|microhd|x26[45]|'
                   r'h\.?26[45]|hevc|castellano|espa[ñn]ol|spanish|dual|ac3|dts|aac|esp|cast)\b.*$', re.I)


def read_env(path=ENV):
    """{clave: valor} del fichero de credenciales (sin comentarios ni líneas vacías)."""
    values = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"\'')
    return values


def missing(env):
    return [k for k in ('api_id', 'api_hash', 'grupo') if not env.get(k)]


def _plain(text):
    """Nombre para comparar: sin mayúsculas, tildes, emojis ni signos."""
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def resolution(width, height):
    """Etiqueta de calidad por el tamaño del vídeo; el ancho manda (2.39:1 en 1080p da 1920×800)."""
    if not width or not height:
        return 'desconocida'
    if width >= 3200 or height >= 1800:
        return '4K'
    if width >= 1800 or height >= 1000:
        return '1080p'
    if width >= 1200 or height >= 700:
        return '720p'
    return 'SD'


def parse_name(text):
    """{title, year, season, episode} de un nombre de fichero o un pie de mensaje; title None si no se entiende."""
    name = (text or '').strip().splitlines()[0] if (text or '').strip() else ''
    name = re.sub(r'\.(mkv|mp4|avi|m4v|mov|ts|webm)$', '', name, flags=re.I)
    name = re.sub(r'^@\w+\s*[-_|]?\s*', '', name)  # «@canal - Título…»
    out = {'title': None, 'year': None, 'season': None, 'episode': None}
    ep = _EPISODE.search(name)
    if ep:
        nums = [g for g in ep.groups() if g]
        out['season'], out['episode'] = int(nums[0]), int(nums[1])
        name = name[:ep.start()]
    year = _YEAR.search(name)
    if year:
        out['year'] = int(year.group(1))
        name = name[:year.start()]
    name = _JUNK.sub('', name)
    name = re.sub(r'[._]+', ' ', name)
    name = re.sub(r'[\s\-–|:\[(]+$', '', re.sub(r'\s+', ' ', name)).strip()
    out['title'] = name or None
    return out


def summarize(videos):
    """Informe de una lista de vídeos [{name, caption, width, height, duration, size}]."""
    qualities = Counter(resolution(v.get('width'), v.get('height')) for v in videos)
    parsed = [parse_name(v.get('name') or v.get('caption')) for v in videos]
    series = [p for p in parsed if p['season']]
    titled = [p for p in parsed if p['title']]
    return {
        'videos': len(videos),
        'gb': round(sum(v.get('size') or 0 for v in videos) / 1e9, 1),
        'calidades': dict(qualities.most_common()),
        'con_titulo': len(titled),
        'con_año': sum(1 for p in parsed if p['year']),
        'capitulos': len(series),
        'series': len({p['title'].lower() for p in series if p['title']}),
        'peliculas': len({(p['title'].lower(), p['year']) for p in titled if not p['season']}),
    }


# --- Telegram (necesita red y la cuenta del usuario) ---------------------------------------------------------------

def _video(msg):
    from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo
    doc = msg.document
    if not doc or not (doc.mime_type or '').startswith('video/'):
        return None
    info = {'id': msg.id, 'size': doc.size, 'caption': msg.message or '', 'name': None,
            'width': None, 'height': None, 'duration': None}
    for attr in doc.attributes:
        if isinstance(attr, DocumentAttributeVideo):
            info.update(width=attr.w, height=attr.h, duration=attr.duration)
        elif isinstance(attr, DocumentAttributeFilename):
            info['name'] = attr.file_name
    return info


async def _login(client):
    from telethon.errors import SessionPasswordNeededError
    import qrcode
    await client.connect()
    if await client.is_user_authorized():
        return
    import qrcode.image.pure
    qr = await client.qr_login()
    try:
        while True:
            # En imagen: el QR dibujado con caracteres en la terminal no lo lee bien la cámara
            qrcode.make(qr.url, image_factory=qrcode.image.pure.PyPNGImage, box_size=12, border=4).save(QR_PNG)
            os.chmod(QR_PNG, 0o600)
            subprocess.run(['open', QR_PNG])
            print('\nEn el móvil: Telegram → Ajustes → Dispositivos → Vincular dispositivo, y escanea el QR de la'
                  ' ventana que se acaba de abrir (caduca en un minuto; luego sale otro).')
            try:
                await qr.wait(timeout=60)
                return
            except SessionPasswordNeededError:
                await client.sign_in(password=getpass.getpass('Contraseña de verificación en dos pasos (no se ve): '))
                return
            except TimeoutError:
                print('El código caducó; ahí va otro.')
                await qr.recreate()
    finally:
        if os.path.exists(QR_PNG):
            os.remove(QR_PNG)


async def _group(client, wanted):
    if re.fullmatch(r'-?\d+', wanted):
        return await client.get_entity(int(wanted))
    if wanted.startswith(('http', '@', 't.me')):
        return await client.get_entity(wanted)
    groups = [d async for d in client.iter_dialogs() if d.is_group or d.is_channel]
    for test in (lambda name: name == _plain(wanted), lambda name: _plain(wanted) in name):
        found = [d for d in groups if test(_plain(d.name))]
        if len(found) == 1:
            return found[0].entity
    print('\nNo sé cuál es el grupo. Estos son tus grupos y canales; copia el nombre del bueno en «grupo»:')
    for d in groups:
        print('  ·', d.name)
    sys.exit(1)


async def _speed(client, msg):
    start, got = time.monotonic(), 0
    async for chunk in client.iter_download(msg.media, request_size=512 * 1024):
        got += len(chunk)
        if got >= SAMPLE_MB * 1024 * 1024:
            break
    seconds = time.monotonic() - start
    return round(got * 8 / seconds / 1e6, 1)  # Mbit/s


async def _topics(client, group):
    """Los temas (carpetas) del grupo que interesan: «Series» y «Películas». [(id, título)]; vacío si no es un foro."""
    from telethon.tl.functions.messages import GetForumTopicsRequest
    if not getattr(group, 'forum', False):
        return []
    result = await client(GetForumTopicsRequest(group, offset_date=None, offset_id=0, offset_topic=0, limit=100))
    print('\nTemas del grupo:', ' · '.join(t.title for t in result.topics if hasattr(t, 'title')))
    return [(t.id, t.title) for t in result.topics if hasattr(t, 'title') and wanted_topic(t.title)]


def wanted_topic(title):
    name = _plain(title)
    return any(word.startswith(('serie', 'peli')) for word in name.split())


async def main():
    from telethon import TelegramClient
    from telethon.tl.types import InputMessagesFilterVideo
    env = read_env()
    if missing(env):
        sys.exit('Falta rellenar en %s: %s' % (ENV, ', '.join(missing(env))))
    client = TelegramClient(SESSION, int(env['api_id']), env['api_hash'])
    await _login(client)
    for path in (SESSION + '.session',):
        if os.path.exists(path):
            os.chmod(path, 0o600)
    group = await _group(client, env['grupo'])
    topics = await _topics(client, group) or [(None, 'todo el grupo')]
    report, videos, sample = {}, [], None
    for topic_id, title in topics:
        print('\nLeyendo los vídeos de «%s»…' % title)
        found = []
        async for msg in client.iter_messages(group, filter=InputMessagesFilterVideo, reply_to=topic_id):
            video = _video(msg)
            if video:
                video['tema'] = title
                found.append(video)
                if sample is None and resolution(video['width'], video['height']) == '1080p':
                    sample = msg
                if len(found) % 500 == 0:
                    print('  %d…' % len(found))
        report[title] = summarize(found)
        report[title]['ejemplos'] = [{'nombre': v['name'] or v['caption'][:80],
                                      'calidad': resolution(v['width'], v['height']),
                                      'entendido': parse_name(v['name'] or v['caption'])}
                                     for v in found[::max(1, len(found) // 40)][:40]]
        videos += found
    report['mbit_s'] = await _speed(client, sample) if sample else None
    await client.disconnect()
    for path, data in ((REPORT, report), (VIDEOS, videos)):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.chmod(path, 0o600)
    for title in (t for _, t in topics):
        r = report[title]
        print('\n«%s»: %d vídeos, %s GB · calidades %s' % (title, r['videos'], r['gb'], r['calidades']))
        print('  con título: %(con_titulo)d · con año: %(con_año)d · capítulos: %(capitulos)d (%(series)d series)'
              ' · películas: %(peliculas)d' % r)
    print('\nDescarga: %s Mbit/s (un 1080p necesita ~10)' % report['mbit_s'])
    print('Informe completo en', REPORT)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
