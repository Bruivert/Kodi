# -*- coding: utf-8 -*-
"""Informe para mandar a quien mantiene el paquete. Nunca incluye valores de ajustes,
claves ni códigos: solo nombres, rutas y versiones. Puro: sin Kodi."""
import re
import xml.etree.ElementTree as ET

TELEGRAM_RE = re.compile(r'(?:https?://)?((?:t|telegram)\.me/[A-Za-z0-9_+/\-]+)')
SECRET_PARAM_RE = re.compile(
    r'([?&](?:[^=&]*(?:code|codigo|token|key|pass|pin|auth|secret)[^=&]*)=)[^&]*', re.I)


def redact(path):
    """Tapa el valor de parámetros tipo code/token/key/pin en una ruta."""
    return SECRET_PARAM_RE.sub(r'\1***', path or '')


def find_telegram_links(text):
    seen = []
    for m in TELEGRAM_RE.finditer(text or ''):
        link = m.group(1).rstrip('/')
        if link not in seen:
            seen.append(link)
    return seen


def setting_ids(settings_xml):
    try:
        root = ET.fromstring(settings_xml)
    except ET.ParseError:
        return []
    return [s.get('id') for s in root.iter('setting') if s.get('id')]


def _rutas_lines(rutas, prefix=''):
    lines = []
    for key, value in (rutas or {}).items():
        if isinstance(value, dict) and 'path' in value:
            lines.append('  %s%s: %s  ->  %s' % (prefix, key, value.get('label', ''), redact(value['path'])))
        elif isinstance(value, dict):
            lines += _rutas_lines(value, prefix + key + '.')
        elif key == 'id':
            lines.append('  %sid: %s' % (prefix, value))
    return lines


def build_report(info):
    out = ['INFORME KODI DE PAPÁ', '=' * 20,
           'Kodi: %s' % info.get('kodi', '?'),
           'Skin: %s' % info.get('skin', '?'), '', 'Addons:']
    addons = info.get('addons') or {}
    out += ['  %s %s' % (k, v) for k, v in addons.items()] or ['  (no encontrado)']
    out += ['', 'Menús de los addons:']
    trees = info.get('trees') or {}
    if not trees:
        out.append('  (no encontrado)')
    for name, rows in trees.items():
        out.append('[%s]' % name)
        out += ['  %s%s  ->  %s' % ('  ' * depth, label, redact(path)) for depth, label, path in rows]
    out += ['', 'Enlaces de Telegram en BlackGhost:']
    out += ['  %s' % link for link in info.get('telegram') or []] or ['  (no encontrado)']
    out += ['', 'Nombres de ajustes de BlackGhost (sin valores):']
    out += ['  %s' % s for s in info.get('bg_setting_ids') or []] or ['  (no encontrado)']
    out += ['', 'Rutas elegidas para el menú:']
    out += _rutas_lines(info.get('rutas')) or ['  (no encontrado)']
    out += ['', 'Claves configuradas:']
    out += ['  %s: %s' % (k, 'sí' if v else 'no') for k, v in (info.get('keys_present') or {}).items()]
    return '\n'.join(out) + '\n'
