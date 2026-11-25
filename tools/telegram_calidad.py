# -*- coding: utf-8 -*-
"""La calidad real de los vídeos del catálogo que Telegram no describe.  venv/bin/python tools/telegram_calidad.py [N]

Crítica del 25/11/2026: el 39 % de las películas y el 55 % de los capítulos del grupo tenían calidad «?» (casi todo
.mkv y .avi, que Telegram no describe). La resolución está en los primeros bytes de cada fichero: se bajan 64 KB de
cada uno (1,8 GB en total para ~28.000 vídeos, frente a 28 TB enteros), se lee (telegram_idx.probe_resolution) y se
apunta en ~/.config/kodi-papa/resoluciones.json {mensaje: [ancho, alto] o null}. Se puede cortar y retomar: lo ya
leído no se repite. Luego se pasa al catálogo con --aplicar (actualiza la calidad en telegram.db).
"""
import asyncio
import json
import os
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'src', 'script.papa.inicio'))
from tools import telegram_fase0 as t0  # noqa: E402
from resources.lib import telegram_idx as ti  # noqa: E402

OUT = os.path.join(t0.CONFIG, 'resoluciones.json')
DB = os.path.join(t0.CONFIG, 'telegram.db')
GRUPO = os.path.join(t0.CONFIG, 'grupo.json')
HEAD = 64 * 1024
WORKERS = 6


def pending(db, done):
    rows = db.execute("SELECT msg FROM pelis WHERE calidad = '?' UNION SELECT msg FROM capitulos WHERE calidad = '?' "
                      "UNION SELECT msg FROM partes").fetchall()
    return sorted({m for m, in rows} - {int(k) for k in done}, reverse=True)  # lo más nuevo primero


def save(done):
    tmp = OUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(done, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, OUT)


async def main(limit):
    from telethon import TelegramClient
    env = t0.read_env()
    grupo = json.load(open(GRUPO, encoding='utf-8'))
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = pending(sqlite3.connect(DB), done)[:limit]
    print('%d vídeos por leer (%d ya leídos)' % (len(todo), len(done)))
    client = TelegramClient(t0.SESSION, int(env['api_id']), env['api_hash'])
    await client.connect()
    group = await client.get_entity(grupo['grupo'])
    queue = asyncio.Queue()
    start, count = time.time(), [0]

    async def worker():
        while True:
            batch = await queue.get()
            try:
                for m in await client.get_messages(group, ids=batch):
                    if not m or not m.media:
                        continue
                    data = b''
                    try:
                        async for chunk in client.iter_download(m.media, request_size=HEAD, limit=1):
                            data = chunk
                    except Exception as exc:
                        print('  %d: %s' % (m.id, type(exc).__name__))
                    done[str(m.id)] = ti.probe_resolution(data)
                    count[0] += 1
                if count[0] % 500 < len(batch):
                    save(done)
                    rate = count[0] / max(1, time.time() - start)
                    print('  %d/%d · %.1f por segundo' % (count[0], len(todo), rate))
            finally:
                queue.task_done()
    for i in range(0, len(todo), 50):
        queue.put_nowait(todo[i:i + 50])
    tasks = [asyncio.create_task(worker()) for _ in range(WORKERS)]
    await queue.join()
    for task in tasks:
        task.cancel()
    await client.disconnect()
    save(done)
    print('hecho: %d leídos en %.0f s' % (count[0], time.time() - start))


def apply():
    """Pasa lo leído al catálogo: la calidad «?» se cambia por la que dice la resolución real."""
    done = json.load(open(OUT))
    db = sqlite3.connect(DB)
    changed = {}
    for msg, wh in done.items():
        label = ti.resolution(*wh) if wh else None
        if not label:
            continue
        for table in ('pelis', 'capitulos'):
            n = db.execute("UPDATE %s SET calidad = ? WHERE msg = ? AND calidad = '?'" % table, (label, int(msg))).rowcount
            if n:
                changed[label] = changed.get(label, 0) + n
    db.commit()
    print('calidades puestas:', changed)


if __name__ == '__main__':
    if '--aplicar' in sys.argv:
        apply()
    else:
        n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 10 ** 6)
        asyncio.run(main(n))
