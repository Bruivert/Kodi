# -*- coding: utf-8 -*-
"""Construye el repositorio Kodi para GitHub Pages: python3 tools/build_repo.py [src] [docs]"""
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

SKIP_DIRS = {'__pycache__', '.git', '.pytest_cache'}
SKIP_EXT = ('.pyc', '.pyo')
ASSETS = ('icon.png', 'fanart.jpg')


def _addon_info(addon_dir):
    path = os.path.join(addon_dir, 'addon.xml')
    root = ET.parse(path).getroot()
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if text.startswith('<?xml'):
        text = text.split('?>', 1)[1]
    return root.get('id'), root.get('version'), text.strip()


def _zip_addon(addon_dir, addon_id, dest):
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(addon_dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name.endswith(SKIP_EXT) or name == '.DS_Store':
                    continue
                full = os.path.join(folder, name)
                z.write(full, addon_id + '/' + os.path.relpath(full, addon_dir).replace(os.sep, '/'))


def build(src_dir, out_dir):
    zips = os.path.join(out_dir, 'zips')
    shutil.rmtree(zips, ignore_errors=True)
    os.makedirs(zips)
    for old in os.listdir(out_dir):
        if old.endswith('.zip'):
            os.remove(os.path.join(out_dir, old))
    result, xmls, repo_zip = [], [], None
    for name in sorted(os.listdir(src_dir)):
        addon_dir = os.path.join(src_dir, name)
        if not os.path.isfile(os.path.join(addon_dir, 'addon.xml')):
            continue
        addon_id, version, text = _addon_info(addon_dir)
        target = os.path.join(zips, addon_id)
        os.makedirs(target)
        zip_path = os.path.join(target, '%s-%s.zip' % (addon_id, version))
        _zip_addon(addon_dir, addon_id, zip_path)
        for asset in ASSETS:
            if os.path.exists(os.path.join(addon_dir, asset)):
                shutil.copy(os.path.join(addon_dir, asset), target)
        if addon_id.startswith('repository.'):
            repo_zip = os.path.basename(zip_path)
            shutil.copy(zip_path, out_dir)
        result.append((addon_id, version))
        xmls.append(text)
    data = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
            + '\n'.join(xmls) + '\n</addons>\n').encode('utf-8')
    with open(os.path.join(zips, 'addons.xml'), 'wb') as f:
        f.write(data)
    with open(os.path.join(zips, 'addons.xml.md5'), 'w') as f:
        f.write(hashlib.md5(data).hexdigest())
    links = '<a href="%s">%s</a>\n' % (repo_zip, repo_zip) if repo_zip else ''
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>Kodi de Papá</title></head>\n'
                '<body>\n%s</body></html>\n' % links)
    open(os.path.join(out_dir, '.nojekyll'), 'w').close()
    return result


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'src')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', 'docs')
    for addon_id, version in build(src, out):
        print('%s %s' % (addon_id, version))
