# -*- coding: utf-8 -*-
"""Todos los mensajes de los temas Películas y Series del grupo: fotos (carátulas), vídeos y textos, en orden.
venv/bin/python tools/telegram_mensajes.py

En el grupo cada título suele empezar con una foto (la carátula) con el nombre, el año y la sinopsis, y debajo sus
vídeos, que a veces solo dicen «1», «2»… (capítulos o partes). Para saber qué es cada vídeo hace falta esa foto.
Leer en orden (sin el filtro de vídeos de la búsqueda) es rápido: ~2.000 mensajes en 7 s. Usa la sesión y el
grupo de ~/.config/kodi-papa (telegram.env, grupo.json) y deja ~/.config/kodi-papa/mensajes.json (600).
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import telegram_fase0 as t0  # noqa: E402

OUT = os.path.join(t0.CONFIG, 'mensajes.json')
GRUPO = os.path.join(t0.CONFIG, 'grupo.json')


def _row(m, tema):
    kind = 'foto' if m.photo else 'video' if m.document and (m.document.mime_type or '').startswith('video/') else \
        'otro' if m.media else 'texto'
    row = {'id': m.id, 'tema': tema, 'tipo': kind, 'caption': m.message or '', 'grupo': m.grouped_id}
    if kind == 'video':
        f = m.file
        row.update(name=f.name or None, width=f.width or None, height=f.height or None, size=f.size or 0,
                   duration=f.duration or None)
    return row


async def main():
    from telethon import TelegramClient
    env = t0.read_env()
    grupo = json.load(open(GRUPO, encoding='utf-8'))
    client = TelegramClient(t0.SESSION, int(env['api_id']), env['api_hash'])
    await client.connect()
    if not await client.is_user_authorized():
        sys.exit('La sesión de Telegram no está abierta: ejecuta antes tools/telegram_fase0.py')
    group = await client.get_entity(grupo['grupo'])
    rows, start = [], time.time()
    for topic, tema in grupo['temas'].items():
        n = 0
        async for m in client.iter_messages(group, reply_to=int(topic)):
            rows.append(_row(m, tema))
            n += 1
            if n % 10000 == 0:
                print('  %s: %d…' % (tema, n))
        print('%s: %d mensajes' % (tema, n))
    await client.disconnect()
    rows.sort(key=lambda r: r['id'])
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False)
    os.chmod(OUT, 0o600)
    print('%d mensajes en %.0f s → %s' % (len(rows), time.time() - start, OUT))


if __name__ == '__main__':
    asyncio.run(main())
