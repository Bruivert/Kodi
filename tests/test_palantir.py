from resources.lib import palantir as pa


def test_links_are_decrypted_like_palantir_does():
    url = 'https://1fichier.com/?abcdef123456&af=99'
    link = pa.encrypt(url)
    assert not link.startswith('http') and pa.decrypt(link) == url
    assert pa.decrypt('https://ya.es/una/direccion') == 'https://ya.es/una/direccion'
    assert pa.decrypt('') == '' and pa.decrypt('no es base64 ni nada') == ''


def test_best_links_spanish_and_1080p_first():
    links = [{'link': 'a', 'calidad': '4K HDR10', 'audio': 'eng,esp'}, {'link': 'b', 'calidad': 'SD', 'audio': 'esp'},
             {'link': 'c', 'calidad': '1080p (R)', 'audio': 'esp'}, {'link': 'd', 'calidad': '1080p', 'audio': 'eng'},
             {'link': 'e', 'calidad': 'DV HDR10', 'audio': 'esp'}, {'link': 'f', 'calidad': '1080p', 'audio': 'esp,eng'},
             {'link': 'g', 'calidad': 'HD', 'audio': 'esp'}, {'link': 'h', 'calidad': '4K', 'audio': 'esp'}]
    assert [l['link'] for l in pa.best(links)] == ['f', 'c', 'h', 'a', 'e']
    assert pa.best(None) == []
