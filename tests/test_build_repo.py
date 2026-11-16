import hashlib
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile

from tools import build_repo, make_icons

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')


def built(tmp_path):
    src = tmp_path / 'src'
    shutil.copytree(SRC, src)
    (src / 'script.papa.inicio' / 'resources' / '__pycache__').mkdir(exist_ok=True)
    (src / 'script.papa.inicio' / 'resources' / '__pycache__' / 'x.pyc').write_bytes(b'junk')
    out = tmp_path / 'docs'
    (out / 'superpowers').mkdir(parents=True)
    (out / 'superpowers' / 'keep.md').write_text('keep')
    return build_repo.build(str(src), str(out)), out


def test_build_lists_both_addons_in_addons_xml(tmp_path):
    result, out = built(tmp_path)
    ids = {i for i, _ in result}
    assert ids == {'repository.papa', 'script.papa.inicio'}
    root = ET.parse(str(out / 'zips' / 'addons.xml')).getroot()
    assert root.tag == 'addons'
    assert {a.get('id') for a in root.findall('addon')} == ids


def test_md5_matches_addons_xml(tmp_path):
    _, out = built(tmp_path)
    data = (out / 'zips' / 'addons.xml').read_bytes()
    assert (out / 'zips' / 'addons.xml.md5').read_text().strip() == hashlib.md5(data).hexdigest()


def test_zips_have_addon_folder_at_root_and_no_pycache(tmp_path):
    result, out = built(tmp_path)
    for addon_id, version in result:
        path = out / 'zips' / addon_id / ('%s-%s.zip' % (addon_id, version))
        names = zipfile.ZipFile(str(path)).namelist()
        assert '%s/addon.xml' % addon_id in names
        assert all(n.startswith(addon_id + '/') for n in names)
        assert not any('__pycache__' in n or n.endswith('.pyc') for n in names)


def test_pages_root_has_repo_zip_index_and_nojekyll_and_keeps_other_docs(tmp_path):
    result, out = built(tmp_path)
    version = dict(result)['repository.papa']
    zip_name = 'repository.papa-%s.zip' % version
    assert (out / zip_name).exists()
    assert 'href="%s"' % zip_name in (out / 'index.html').read_text()
    assert (out / '.nojekyll').exists()
    assert (out / 'superpowers' / 'keep.md').exists()


def test_repository_points_to_pages_and_jurialmunkey_omega():
    root = ET.parse(os.path.join(SRC, 'repository.papa', 'addon.xml')).getroot()
    dirs = root.findall('.//dir')
    assert dirs[0].find('info').text == 'https://bruivert.github.io/Kodi/zips/addons.xml'
    assert dirs[0].find('datadir').text == 'https://bruivert.github.io/Kodi/zips/'
    jm = 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/'
    assert dirs[1].get('minversion') == '20.9.1'
    assert dirs[1].find('datadir').text == jm
    assert dirs[1].find('info').text == jm + 'addons.xml'
    # Arctic Fuse 3 needs resource.images.arctic.* which live in jurialmunkey's version-agnostic repo/zips
    common = 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/repo/zips/'
    assert dirs[2].get('minversion') is None
    assert dirs[2].find('datadir').text == common
    assert dirs[2].find('info').text == common + 'addons.xml'
    assert dirs[2].find('checksum').text == common + 'addons.xml.md5'


def test_make_icon_writes_valid_png(tmp_path):
    path = tmp_path / 'icon.png'
    make_icons.write_icon(str(path), size=64)
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert int.from_bytes(data[16:20], 'big') == 64 and int.from_bytes(data[20:24], 'big') == 64
