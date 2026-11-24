# -*- coding: utf-8 -*-
"""Fase 1: catálogo del grupo de Telegram.  venv/bin/python tools/telegram_indexar.py

Lee la lista que dejó la fase 0 (~/.config/kodi-papa/fase0_videos.json, temas Películas y Series), se queda con lo
que está en castellano (en Telegram no se exige 1080p) y lo cruza con TMDb. Escribe el catálogo en
~/.config/kodi-papa/telegram.db y un informe en telegram_informe.json. La clave de TMDb se lee de los ajustes del
asistente en la caja (por ADB) y no se escribe en ningún sitio. Las respuestas de TMDb se guardan en
tmdb_cache.json: repetir el indexado no vuelve a preguntar.
"""
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib import error, parse, request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'script.papa.inicio'))
from resources.lib import telegram_idx as ti  # noqa: E402

CONFIG = os.path.expanduser('~/.config/kodi-papa')
VIDEOS = os.path.join(CONFIG, 'fase0_videos.json')
DB = os.path.join(CONFIG, 'telegram.db')
CACHE = os.path.join(CONFIG, 'tmdb_cache.json')
REPORT = os.path.join(CONFIG, 'telegram_informe.json')
GRUPO = os.path.join(CONFIG, 'grupo.json')  # número del grupo y de sus temas: privado, fuera del repositorio
ADB = os.path.expanduser('~/Library/Android/sdk/platform-tools/adb')
SETTINGS = '/storage/emulated/0/Android/data/org.xbmc.kodi/files/.kodi/userdata/addon_data/script.papa.inicio/settings.xml'
TMDB = 'https://api.themoviedb.org/3/'


def tmdb_key():
    xml = subprocess.run([ADB, 'shell', 'su 0 cat ' + SETTINGS], capture_output=True, text=True).stdout
    found = re.search(r'<setting id="tmdb_key"[^>]*>([^<]+)<', xml)
    if not found:
        sys.exit('No encuentro la clave de TMDb en la caja (¿está conectada?).')
    return found.group(1).strip()


class Tmdb:
    def __init__(self, key):
        self.key = key
        self.cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
        self.asked = 0

    def search(self, kind, query, year=None):
        params = {'language': 'es-ES', 'include_adult': 'false', 'query': query}
        if year:
            params['year' if kind == 'movie' else 'first_air_date_year'] = year
        tag = '%s|%s|%s' % (kind, query, year or '')
        if tag not in self.cache:
            url = TMDB + 'search/%s?%s' % (kind, parse.urlencode(dict(params, api_key=self.key)))
            for attempt in range(5):
                try:
                    with request.urlopen(url, timeout=15) as r:
                        self.cache[tag] = json.loads(r.read().decode('utf-8')).get('results', [])[:10]
                    self.asked += 1
                    break
                except error.HTTPError as exc:
                    if exc.code != 429:
                        self.cache[tag] = []
                        break
                    time.sleep(2 + attempt * 2)
                except (error.URLError, TimeoutError):
                    time.sleep(2)
            else:
                return []
        return self.cache[tag]

    def save(self):
        with open(CACHE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False)
        os.chmod(CACHE, 0o600)


def main():
    videos = json.load(open(VIDEOS, encoding='utf-8'))
    tmdb = Tmdb(tmdb_key())
    print('Cruzando con TMDb…')
    with ThreadPoolExecutor(8) as pool:
        found = ti.catalogue(videos, tmdb.search, pool.map)
    tmdb.save()
    print('  %d consultas nuevas a TMDb' % tmdb.asked)
    if os.path.exists(DB):
        os.remove(DB)
    db = sqlite3.connect(DB)
    grupo = json.load(open(GRUPO, encoding='utf-8'))
    ti.store(db, found, max(v['id'] for v in videos), grupo['grupo'], {int(k): v for k, v in grupo['temas'].items()})
    count = lambda q: db.execute(q).fetchone()[0]  # noqa: E731
    stats = {'vídeos leídos': len(videos),
             'películas distintas': count('SELECT COUNT(DISTINCT tmdb) FROM pelis'),
             'vídeos de películas': count('SELECT COUNT(*) FROM pelis'),
             'series distintas': count('SELECT COUNT(DISTINCT tmdb) FROM capitulos'),
             'capítulos distintos': count('SELECT COUNT(*) FROM (SELECT DISTINCT tmdb, temporada, capitulo FROM capitulos)'),
             'sin ficha en TMDb': len(found['sin_ficha'])}
    db.close()
    os.chmod(DB, 0o600)
    random.seed(7)
    report = {'resumen': stats, 'muestra': random.sample(found['muestra'], min(30, len(found['muestra']))),
              'sin_ficha': dict(list(found['sin_ficha'].items())[:400])}
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    os.chmod(REPORT, 0o600)
    for k, n in stats.items():
        print('  %-24s %6d' % (k, n))
    print('\nCatálogo en', DB, '· informe en', REPORT)


if __name__ == '__main__':
    main()
