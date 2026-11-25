import urllib.error
import urllib.parse
import urllib.request

from resources.lib import pegar


def test_only_pelis_addresses_are_accepted_and_cleaned():
    assert pegar.clean(' https://pelis-addon.com/eyJhbGciOi.xyz/manifest.json \n') == \
        'https://pelis-addon.com/eyJhbGciOi.xyz'
    assert pegar.clean('stremio://pelis-addon.com/abc/manifest.json') == 'https://pelis-addon.com/abc'
    assert pegar.clean('https://pelis-addon.com/') is None
    assert pegar.clean('https://otra-web.com/abc') is None and pegar.clean('') is None


def test_page_never_shows_the_saved_address():
    assert 'Ya hay una dirección guardada' in pegar.page(saved=True)
    assert 'Aún no hay ninguna' in pegar.page()


def test_server_saves_what_is_pasted():
    box = {}
    server = pegar.serve(lambda: box.get('url'), lambda url: box.update(url=url), port=0)
    port = server.server_address[1]
    try:
        assert 'Aún no hay ninguna' in urllib.request.urlopen('http://127.0.0.1:%d/' % port).read().decode('utf-8')
        body = urllib.parse.urlencode({'url': 'https://pelis-addon.com/SECRETO/manifest.json'}).encode()
        page = urllib.request.urlopen('http://127.0.0.1:%d/' % port, data=body).read().decode('utf-8')
        assert 'Guardada' in page and 'SECRETO' not in page and box['url'] == 'https://pelis-addon.com/SECRETO'
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/' % port, data=b'url=https://mala.com/x')
            assert False
        except urllib.error.HTTPError as exc:
            assert exc.code == 400 and box['url'] == 'https://pelis-addon.com/SECRETO'
    finally:
        server.shutdown()
