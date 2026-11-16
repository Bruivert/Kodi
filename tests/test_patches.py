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
