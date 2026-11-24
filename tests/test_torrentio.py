from resources.lib import torrentio as tt

ES, MX = '\U0001F1EA\U0001F1F8', '\U0001F1F2\U0001F1FD'


def _s(quality, seeds, flags=ES, btih='AB'):
    return {'name': 'Torrentio\n' + quality, 'infoHash': btih,
            'title': 'Reacher [%s][Cap.401]\n\U0001F464 %d \U0001F4BE 3.09 GB ⚙️ Wolfmax4k\n%s' % (quality, seeds, flags)}


def test_addresses():
    assert tt.stream_url('series', 'tt9288030', 4, 1) == tt.BASE + 'stream/series/tt9288030:4:1.json'
    assert tt.stream_url('peliculas', 'tt17526714') == tt.BASE + 'stream/movie/tt17526714.json'
    assert 'wolfmax4k' in tt.BASE and 'language=spanish' in tt.BASE


def test_best_is_spanish_1080p_or_more_1080p_first_then_most_seeded():
    streams = [_s('4k', 1, btih='K1'), _s('1080p', 4, btih='F4'), _s('720p', 18, btih='S'), _s('BluRay', 50, btih='B'),
               _s('1080p', 80, btih='F80'), _s('1080p', 99, MX, btih='LAT'), _s('4k HDR', 30, btih='HDR'),
               _s('4k', 9, ES + ' / ' + MX, btih='K9'), {'name': 'Torrentio\n1080p', 'title': ES}]
    best = tt.best(streams)
    assert [b['btih'] for b in best] == ['f80', 'f4', 'k9', 'k1', 'hdr']
    assert best[0] == {'btih': 'f80', 'quality': '1080p', 'seeds': 80, 'title': 'Reacher [1080p][Cap.401]'}
    assert tt.best(None) == [] and tt.best([{'name': 'x'}]) == []
