# -*- coding: utf-8 -*-
"""Genera icon.png de los addons (degradado oscuro con un botón de play) sin dependencias."""
import os
import struct
import sys
import zlib


def _chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def _pixel(x, y, size):
    t = y / float(size - 1)
    r, g, b = int(20 + 70 * t), int(24 + 10 * t), int(60 + 90 * t)
    # triángulo de play centrado
    cx, cy, h = size * 0.42, size * 0.5, size * 0.22
    if cx - h * 0.6 <= x <= cx + h * 1.1 and abs(y - cy) <= (cx + h * 1.1 - x) * 0.62:
        return 245, 245, 250
    return r, g, b


def write_icon(path, size=512):
    rows = b''.join(b'\x00' + b''.join(bytes(_pixel(x, y, size)) for x in range(size)) for y in range(size))
    png = (b'\x89PNG\r\n\x1a\n'
           + _chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
           + _chunk(b'IDAT', zlib.compress(rows, 9))
           + _chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'src')
    for addon in ('repository.papa', 'script.papa.inicio'):
        write_icon(os.path.join(src, addon, 'icon.png'))
