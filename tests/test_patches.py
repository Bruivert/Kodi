from resources.lib import patches as pt

# Fragmento real de plugin.video.youtube 7.4.4: resources/lib/youtube_plugin/youtube/client/player_client.py
YOUTUBE = """        self._client_groups = (
            ('custom', clients if clients else ()),
            ('auth_enabled|initial_request|no_playable_streams', (
                'tv_unplugged',
                'tv',
            )),
            ('auth_disabled|kids|av1|vp9.2|avc1|surround_sound|multi_audio', (
                'android_testsuite_params',
            )),
            ('auth_enabled|no_kids|av1|vp9.2|avc1|surround_sound', (
                'android_vr',
            )),
            ('mpd', (
            )),
"""

# Fragmento real de skin.arctic.fuse.3 3.5.2: 1080i/Includes_Hubs.xml (las dos variantes del grupo de filas)
AF3 = """                            <!-- Widgets Groups -->
                            <control type="group" id="500">
                                <include content="Hub_Combined_Widgets_Grouplist" condition="x">
                                </include>
                            </control>
                    <control type="group" id="400">
                        <include>Animation_View_WindowChange</include>
                        <!-- Widgets Groups -->
                        <control type="group" id="500">
                            <include content="Hub_Combined_Widgets_Grouplist" condition="y">
                            </include>
                        </control>
"""


def test_youtube_patch_only_disables_the_android_vr_client():
    new = pt.patch_youtube(YOUTUBE)
    assert new is not None
    removed = [line for line in YOUTUBE.splitlines() if line not in new.splitlines()]
    assert removed == ["                'android_vr',"]
    assert "                # 'android_vr',  # disabled by script.papa.inicio" in new
    assert "                'android_testsuite_params'," in new
    assert len(new.splitlines()) == len(YOUTUBE.splitlines())  # el grupo queda vacío y el addon lo salta


def test_youtube_patch_is_applied_once():
    assert pt.patch_youtube(pt.patch_youtube(YOUTUBE)) is None


def test_youtube_patch_leaves_other_code_alone():
    assert pt.patch_youtube(YOUTUBE.replace("'android_vr'", "'android_vr_2'")) is None
    assert pt.patch_youtube('') is None


def test_youtube_patch_only_for_the_broken_version():
    assert pt.youtube_needs_patch('7.4.4')
    assert not pt.youtube_needs_patch('7.4.5')
    assert not pt.youtube_needs_patch('')


def test_af3_patch_fades_both_row_groups_while_our_trailer_plays():
    new = pt.patch_af3_rows(AF3)
    lines = new.splitlines()
    fades = [i for i, line in enumerate(lines) if 'papa.trailer' in line]
    assert len(fades) == 2
    for i in fades:
        assert lines[i - 1].strip() == '<control type="group" id="500">'
        # misma sangría que el primer hijo del grupo
        assert len(lines[i]) - len(lines[i].lstrip()) == len(lines[i + 1]) - len(lines[i + 1].lstrip())
        assert '>Conditional</animation>' in lines[i]
        assert 'System.IdleTime(3)' in lines[i] and '!Window.IsActive(fullscreenvideo)' in lines[i]
    assert [line for line in lines if 'papa.trailer' not in line] == AF3.splitlines()


def test_af3_patch_is_applied_once_and_ignores_other_skins():
    assert pt.patch_af3_rows(pt.patch_af3_rows(AF3)) is None
    assert pt.patch_af3_rows('<control type="group" id="400"/>') is None


def test_af3_fade_condition_uses_the_property_the_service_sets():
    assert 'Window(Home).Property(%s)' % pt.TRAILER_PROPERTY in pt.ROWS_FADE


def test_af3_fade_hides_the_rows_completely_and_gently():
    assert 'start="100" end="0"' in pt.ROWS_FADE  # desaparecen del todo
    assert 'tween="sine"' in pt.ROWS_FADE and 'easing="inout"' in pt.ROWS_FADE  # sin brusquedad
    assert 'time="1500"' in pt.ROWS_FADE


def test_af3_patch_upgrades_the_old_partial_fade():
    old_line = ('<animation effect="fade" start="100" end="25" time="500" condition="String.IsEqual('
                'Window(Home).Property(papa.trailer),1) + System.IdleTime(3) + !Window.IsActive(fullscreenvideo)">'
                'Conditional</animation><!-- script.papa.inicio -->')
    old = pt.patch_af3_rows(AF3).replace(pt.ROWS_FADE, old_line)  # una caja con la 1.0.3/1.0.4
    new = pt.patch_af3_rows(old)
    assert new == pt.patch_af3_rows(AF3)
    assert 'end="25"' not in new
    assert pt.patch_af3_rows(new) is None


class FakeKodi:
    def __init__(self, touched):
        self.touched, self.now, self.quiet = list(touched), 0.0, False
        self.applied, self.reloads = 0, 0

    def apply(self):
        self.applied += 1
        return self.touched.pop(0) if self.touched else []

    def cond(self, expr):
        assert expr == pt.QUIET
        return self.quiet

    def reload(self):
        self.reloads += 1


def keeper(kodi):
    return pt.PatchKeeper(kodi.apply, kodi.cond, kodi.reload, lambda: kodi.now, 'skin.arctic.fuse.3')


def test_keeper_patches_at_start_and_then_every_ten_minutes():
    kodi = FakeKodi([[], [], []])
    k = keeper(kodi)
    k.tick()
    assert kodi.applied == 1
    kodi.now = pt.CHECK_EVERY - 1
    k.tick()
    assert kodi.applied == 1
    kodi.now = pt.CHECK_EVERY
    k.tick()
    assert kodi.applied == 2
    assert kodi.reloads == 0


def test_keeper_reloads_the_skin_only_when_nobody_is_using_kodi():
    # La skin se actualizó sola y Kodi ya la tiene cargada: el fundido no se ve hasta recargarla.
    kodi = FakeKodi([['skin.arctic.fuse.3']])
    k = keeper(kodi)
    k.tick()
    assert kodi.reloads == 0  # tu padre está usando Kodi
    kodi.quiet = True
    k.tick()
    k.tick()
    assert kodi.reloads == 1


def test_keeper_does_not_reload_for_youtube_alone():
    kodi = FakeKodi([['plugin.video.youtube']])
    kodi.quiet = True
    k = keeper(kodi)
    k.tick()
    assert kodi.reloads == 0  # el arreglo de YouTube vale en el siguiente vídeo


def test_keeper_waits_while_something_plays_a_dialog_is_open_or_the_remote_is_in_use():
    for atom in ('!Player.HasMedia', '!System.HasActiveModalDialog', 'System.IdleTime(300)'):
        assert atom in [a.strip() for a in pt.QUIET.split('+')]


# Arctic Fuse 3 3.5.4, 1080i/Includes_Home.xml: la lupa del menú.
AF3_HOME = """    <include name="Home_ControlList_Item_MultiSearch">
        <include content="Home_ControlList_Item">
            <param name="label">$LOCALIZE[137]</param>
            <param name="icon">special://skin/extras/icons/search.png</param>
            <param name="action">RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,progress_dialog$VAR[Value_MultiSearch_Layout_Param]$VAR[Value_MultiSearch_Discover_Param])</param>
            <param name="enabled">[!Skin.HasSetting(HomeSwitcher.DisableSearch)]</param>
        </include>
    </include>
"""


PATCHED_HOME = AF3_HOME.replace(AF3_HOME.splitlines()[4].strip(),
                                '<param name="action">RunScript(script.papa.inicio,buscar)</param>')


def test_search_patch_gives_the_magnifier_back_to_af3():
    assert pt.patch_af3_search(PATCHED_HOME) == AF3_HOME
    assert pt.patch_af3_search(AF3_HOME) is None and pt.patch_af3_search('<includes/>') is None


PO = 'msgctxt "#31016"\nmsgid "Sort by"\nmsgstr "Ordenar por"\n\nmsgctxt "#31851"\nmsgid "Sources"\nmsgstr ""\n'


def test_missing_spanish_texts_are_added_once():
    new = pt.patch_af3_strings(PO)
    assert 'msgctxt "#31851"\nmsgid "Sources"\nmsgstr "Fuentes"' in new
    assert 'msgctxt "#31865"\nmsgid "Enter a search term to begin."\nmsgstr "Escribe lo que quieres ver."' in new
    assert new.count('msgctxt "#31851"') == 1 and 'msgstr "Ordenar por"' in new
    assert pt.patch_af3_strings(new) is None
    sv = pt.patch_skinvariables_strings('')
    assert 'msgctxt "#32104"\nmsgid "Searching \\"{}\\""\nmsgstr "Buscando «{}»"' in sv and 'msgstr "Todos"' in sv


# Arctic Fuse 3 3.5.4, 1080i/script-skinvariables-images-includes.xml (recortado): la imagen de las tarjetas.
_EP = ('<value condition="[String.IsEqual({li}.DBType,episode) | String.IsEqual({li}.DBType,video) | '
       'String.IsEqual({li}.DBType,musicvideo)] + !String.IsEmpty({li}.Art(thumb)) + '
       'String.IsEqual({li}.Icon,{li}.Art(thumb)) + !String.IsEqual({li}.Art(thumb),{li}.Art(poster))">'
       '$INFO[{li}.Art(thumb)]</value>')
IMAGES = '''<includes>
    <variable name="Image_Landscape">
        <value condition="String.IsEqual(ListItem.Property(tmdb_type),person)" />
        %s
        <value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value>
    </variable>
    <variable name="Image_Landscape_LIA_C450_0">
        %s
        <value condition="!String.IsEmpty(Container(450).ListItemAbsolute(0).Art(fanart))">$INFO[Container(450).ListItemAbsolute(0).Art(fanart)]</value>
    </variable>
</includes>
''' % (_EP.format(li='ListItem'), _EP.format(li='Container(450).ListItemAbsolute(0)'))


def test_episode_cards_show_their_own_still_instead_of_the_show_fanart():
    # Palantir pone la foto del capítulo también como carátula y AF3, al verlas iguales, pinta el fondo de la serie
    # en todos los capítulos. Con la foto propia (still) delante, cada capítulo sale con la suya.
    new = pt.patch_af3_episode_thumbs(IMAGES)
    for li in ('ListItem', 'Container(450).ListItemAbsolute(0)'):
        still = ('<value condition="String.IsEqual({li}.DBType,episode) + !String.IsEmpty({li}.Art(still)) + '
                 '!String.IsEqual({li}.Icon,OverlaySpoiler.png)">$INFO[{li}.Art(still)]</value>').format(li=li)
        assert new.count(still) == 1
        assert new.index(still) < new.index(_EP.format(li=li))  # antes de la regla de AF3
    assert new.replace('\n', '').count('<value') == IMAGES.replace('\n', '').count('<value') + 2
    assert pt.patch_af3_episode_thumbs(new) is None  # una sola vez
    assert pt.patch_af3_episode_thumbs('<includes/>') is None


BALANDRO_PLAY = ('def play_from_itemlist(itemlist, parent_item):\n'
                 '    from core import servertools\n\n'
                 '    itemlist = servertools.filter_and_sort_by_quality(itemlist)\n'
                 '    itemlist = servertools.filter_and_sort_by_server(itemlist)\n')


def test_balandro_plays_only_1080p_movies_and_leaves_episodes_to_the_assistant():
    import re
    new = pt.patch_balandro_quality(BALANDRO_PLAY)
    assert new and pt.patch_balandro_quality(new) is None and pt.patch_balandro_quality('otra versión') is None

    class It(object):
        def __init__(self, quality, kind='movie'):
            self.quality, self.contentType = quality, kind

    env = {'re': re}
    exec(compile(new.replace('    from core import servertools\n', '').replace(
        'servertools.filter_and_sort_by_quality(itemlist)', 'itemlist').replace(
        '    itemlist = servertools.filter_and_sort_by_server(itemlist)\n', '    return itemlist\n'), 'p', 'exec'), env)
    links = [It('720p'), It('1080p'), It(''), It('4K'), It(None)]
    assert [i.quality for i in env['play_from_itemlist'](links, It('', 'movie'))] == ['1080p', '4K']
    assert len(env['play_from_itemlist'](links, It('', 'episode'))) == 5


DT_SEARCH = ("    data = do_downloadpage(item.url, post = post, headers = headers)\n\n"
             "    bloque = scrapertools.find_single_match(data, '>Resultados<(.*?)</nav>')\n\n"
             "    patron = \"<a href='(.*?)'.*?\"\n"
             "    patron += 'class=\"text-decoration-none\">(.*?)</a>'\n\n"
             "    matches = re.compile(patron).findall(bloque)\n")


def test_dontorrents_search_reads_the_new_results_page():
    import re
    new = pt.patch_dontorrents_search(DT_SEARCH)
    assert new and pt.patch_dontorrents_search(new) is None
    page = ('<h1>Resultados</h1><ul class="search-results"><li><a href="/serie/92796/92797/La-playlist-1-Temporada" '
            'class="search-result-link text-decoration-none"><span class="text-secondary">La</span> playlist</a></li>'
            '</ul>')
    env = {'re': re, 'data': page, 'scrapertools': type('S', (), {'find_single_match': staticmethod(
        lambda d, p: (re.search(p, d, re.S).group(1) if re.search(p, d, re.S) else ''))})}
    exec(new.replace('    data = do_downloadpage(item.url, post = post, headers = headers)\n', '').replace(
        '\n    ', '\n').lstrip(), env)
    assert env['matches'] == [('/serie/92796/92797/La-playlist-1-Temporada',
                               '<span class="text-secondary">La</span> playlist')]


def test_telegram_topic_patch():
    from resources.lib import patches as pt
    text = 'x = {\n        "ext": ".jpg",\n    }\n    if kind == "video":\n'
    new = pt.patch_telegram_topic(text)
    assert '"topic": ((m.reply_to.reply_to_top_id or m.reply_to.reply_to_msg_id)' in new
    assert pt.patch_telegram_topic(new) is None and pt.patch_telegram_topic('otra versión') is None
