import hashlib

from resources.lib import debrid as db


def _benc(value):
    if isinstance(value, int):
        return b'i%de' % value
    if isinstance(value, bytes):
        return b'%d:%s' % (len(value), value)
    if isinstance(value, list):
        return b'l' + b''.join(_benc(v) for v in value) + b'e'
    return b'd' + b''.join(_benc(k) + _benc(v) for k, v in sorted(value.items())) + b'e'


def test_info_hash_is_the_sha1_of_the_info_dictionary():
    info = {b'name': b'Tony (2026) Web-Dl 1080p.mkv', b'length': 6356000000, b'piece length': 4194304,
            b'pieces': b'x' * 40, b'files': [{b'length': 1, b'path': [b'a']}]}
    torrent = _benc({b'announce': b'udp://t', b'created by': b'qBittorrent', b'info': info})
    assert db.info_hash(torrent) == hashlib.sha1(_benc(info)).hexdigest()
    assert db.info_hash(b'<html>no es un torrent</html>') is None and db.info_hash(b'd3:fooi1ee') is None


def test_magnet():
    assert db.magnet('abc') == 'magnet:?xt=urn:btih:abc'
    assert db.magnet('abc', 'Tony 1080p') == 'magnet:?xt=urn:btih:abc&dn=Tony%201080p'


def test_hd_links_1080p_first_and_nothing_below():
    links = [('4K', 'u4k'), ('720p', 'u720'), ('1080p', 'u1080'), ('Full HD', 'ufull'), ('', 'unada')]
    assert db.hd_links(links) == ['u1080', 'ufull', 'u4k'] and db.hd_links(None) == []


def test_dontorrent_challenge_answer():
    nonce = db.pow_nonce('cb58d0ba3b26f5204dcc56f7f28e456206147cb4c3d0905c83bf59bcfae92d83')
    assert hashlib.sha256(('cb58d0ba3b26f5204dcc56f7f28e456206147cb4c3d0905c83bf59bcfae92d83' + str(nonce))
                          .encode()).hexdigest().startswith('000')
    assert db.pow_nonce('x', 1) == next(n for n in range(10000)
                                        if hashlib.sha256(('x' + str(n)).encode()).hexdigest().startswith('0'))
