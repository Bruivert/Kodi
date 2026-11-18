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


def test_search_patch_makes_the_magnifier_search_in_palantir():
    new = pt.patch_af3_search(AF3_HOME)
    assert '<param name="action">RunScript(script.papa.inicio,buscar)</param>' in new
    assert 'run_multisearch' not in new
    assert new.count('\n') == AF3_HOME.count('\n')  # solo cambia esa línea


def test_search_patch_is_applied_once_and_ignores_other_skins():
    assert pt.patch_af3_search(pt.patch_af3_search(AF3_HOME)) is None
    assert pt.patch_af3_search('<includes/>') is None
