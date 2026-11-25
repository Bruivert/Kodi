from resources.lib import pelis

BOLT, DISK, SOUND, MAGNET = '⚡', '\U0001F4BE', '\U0001F50A', '\U0001F9F2'


def _s(quality, audio, size=None, cached=True, url='u'):
    title = '\U0001F3AC Tony %s %s' % (SOUND, audio) + (' %s %.2f GB' % (DISK, size) if size else '')
    return {'name': 'AD %s%s' % (BOLT + ' ' if cached else '', quality), 'title': title, 'url': url}


def test_addresses():
    assert pelis.stream_url('https://pelis-addon.com/C', 'peliculas', 'tt1') == \
        'https://pelis-addon.com/C/stream/movie/tt1.json'
    assert pelis.stream_url('https://pelis-addon.com/C', 'series', 'tt2', 4, 1) == \
        'https://pelis-addon.com/C/stream/series/tt2:4:1.json'


def test_best_spanish_ready_1080p_first_lightest_first():
    streams = [_s('4K Dolby Vision HDR10+', 'Inglés - Español', 19.27, url='dv'),
               _s('4K', 'Español', 19.75, url='4k'), _s('1080p', 'Español - Inglés', 7.70, url='f77'),
               _s('1080p', 'Español', 8.09, url='f80'), _s('1080p', 'Latino', 2.0, url='lat'),
               _s('720p', 'Español', 1.0, url='720'), _s('1080p', 'Español', 5.0, cached=False, url='nocache'),
               _s('4K HDR10', 'Español - Inglés', 30.4, url='hdr'), _s('1080p', 'Español', url='nosize'),
               {'name': 'AD %s 1080p' % BOLT, 'title': '%s Español' % SOUND}]
    best = pelis.best(streams)
    assert [b['url'] for b in best] == ['f77', 'f80', 'nosize', '4k', 'hdr', 'dv']
    assert best[0] == {'url': 'f77', 'quality': '1080p', 'size': 7.7}
    assert pelis.best(None) == []
