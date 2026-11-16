from resources.lib import diagnostico as dg

PY = '''
TELEGRAM = "https://t.me/blackghostoficial"
qr = 'telegram.me/joinchat/AbCdEf123'
otro = "t.me/blackghostoficial"  # repetido
'''

SETTINGS = '''<?xml version="1.0" ?>
<settings version="1">
  <section id="plugin.video.blackghost">
    <category id="general">
      <group id="1">
        <setting id="codigo_acceso" type="string"><default>SECRETO123</default></setting>
        <setting id="ultima_fecha" type="string" />
      </group>
    </category>
  </section>
</settings>'''

OLD_SETTINGS = '<settings><setting id="code" type="text" label="Código" default="XYZ" /></settings>'


def test_find_telegram_links_unique_and_both_hosts():
    assert dg.find_telegram_links(PY) == ['t.me/blackghostoficial', 'telegram.me/joinchat/AbCdEf123']


def test_setting_ids_only_never_values():
    assert dg.setting_ids(SETTINGS) == ['codigo_acceso', 'ultima_fecha']
    assert dg.setting_ids(OLD_SETTINGS) == ['code']
    assert dg.setting_ids('not xml') == []


def test_report_lists_trees_links_and_key_presence_without_values():
    info = {
        'kodi': '21.2', 'skin': 'skin.arctic.fuse.3',
        'addons': {'plugin.video.palantir3': '3.1.0', 'plugin.video.blackghost': '4.0.2'},
        'trees': {'BlackGhost': [(0, 'Deportes', 'plugin://bg/?d'), (1, 'Fútbol', 'plugin://bg/?f')]},
        'telegram': ['t.me/blackghostoficial'],
        'bg_setting_ids': ['codigo_acceso'],
        'rutas': {'blackghost': {'deportes': {'futbol': {'label': 'Fútbol', 'path': 'plugin://bg/?f'}}}},
        'keys_present': {'TMDb': True, 'OMDb': False},
    }
    text = dg.build_report(info)
    for expected in ['21.2', 'skin.arctic.fuse.3', 'plugin.video.palantir3 3.1.0', 'Deportes',
                     '    Fútbol  ->  plugin://bg/?f', 't.me/blackghostoficial', 'codigo_acceso',
                     'TMDb: sí', 'OMDb: no']:
        assert expected in text, expected
    assert 'SECRETO123' not in text


def test_report_with_nothing_found():
    text = dg.build_report({})
    assert 'no encontrado' in text.lower()
