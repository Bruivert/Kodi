from resources.lib import calidad as ca

ROW = ('<tbody><tr><td>x</td><td>y</td><td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300">%s </td>'
       '<td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300 text-center">3.61GB. </td>'
       '<a href="/t.torrent">D</a></tr></tbody>')


def test_hd_is_1080p_or_more():
    for q in ('1080p', 'BluRay 1080p', '4K', 'UHD 2160p', 'Full HD', 'WEB-DL 1080p', 'Dual 1080p'):
        assert ca.is_hd(q), q
    for q in ('720p', 'HDTV-720p', 'DVDRip', 'HQ-TS', 'MicroHD', 'HDRip', '', None, '4KB'):
        assert not ca.is_hd(q), q


def test_pasateatorrent_page_qualities():
    assert ca.pasate_qualities(ROW % '720p') == ['720p']
    assert ca.pasate_qualities('\n'.join([ROW % '4K', ROW % '1080p'])) == ['4K', '1080p']
    assert ca.pasate_qualities('<html>otra web</html>') == [] and ca.pasate_qualities(None) == []
    assert ca.any_hd(['720p', '4K']) and not ca.any_hd(['720p']) and not ca.any_hd([])


def test_episode_quality_from_size_and_length():
    assert ca.size_gb('0.67GB') == 0.67 and ca.size_gb('1,5 GB') == 1.5 and ca.size_gb('700 MB') == 0.7
    assert ca.size_gb('Descargar') is None
    assert not ca.episode_hd('0.67GB')  # 45 min en 0,67 GB: 720p
    assert ca.episode_hd('1.30GB')
    assert not ca.episode_hd('1.30GB', 60) and ca.episode_hd('1.70GB', 60)
    assert ca.episode_hd('0.70GB', 25)  # comedia de media hora
    assert not ca.episode_hd('', 45) and not ca.episode_hd(None)


EPISODE = ('<tr wire:key=episode-0><td>i</td><td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300">2x%d '
           '</td><td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-300 text-center">%s </td>'
           '<a href="/e.torrent">D</a></tr>')


def test_pasateatorrent_episode_sizes():
    html = '<tbody>' + EPISODE % (1, '0.67GB') + EPISODE % (2, '1.40GB') + '</tbody>'
    assert ca.pasate_sizes(html) == ['0.67GB', '1.40GB']


def test_rows_show_only_pages_with_1080p_and_never_unchecked_ones():
    movie = ca.page_entry('peliculas', ROW % '4K', 100)
    assert movie == {'time': 100, 'q': ['4K'], 'links': [('4K', 'https://pasateatorrent.org/t.torrent')]}
    assert ca.page_ok('peliculas', movie)
    assert not ca.page_ok('peliculas', ca.page_entry('peliculas', ROW % '720p', 100))
    assert not ca.page_ok('peliculas', None) and not ca.page_ok('series', {})
    show = ca.page_entry('series', EPISODE % (1, '0.67GB') + EPISODE % (2, '1.40GB'), 100)
    assert ca.page_ok('series', show) and not ca.page_ok('series', {'q': ['0.6GB']})
    assert ca.fresh(movie, 100 + ca.MAX_AGE - 1) and not ca.fresh(movie, 100 + ca.MAX_AGE) and not ca.fresh(None, 0)
