# -*- coding: utf-8 -*-
"""Arreglos a archivos de otros addons de la caja (con permiso del dueño). Puro: recibe el texto y devuelve el
texto nuevo, o None si no hay nada que cambiar (ya aplicado, otra versión u otra skin)."""
import re

MARK = 'script.papa.inicio'

# YouTube 7.4.4: Google corta con 403 los vídeos que pide con el cliente ANDROID_VR y la imagen se congela.
# Sin ese cliente usa los otros (testsuite) y los tráileres suenan enteros. Incidencia #1483 del addon.
YOUTUBE_FILE = 'resources/lib/youtube_plugin/youtube/client/player_client.py'
YOUTUBE_BROKEN = ('7.4.4',)
_YOUTUBE_OLD = "('auth_enabled|no_kids|av1|vp9.2|avc1|surround_sound', (\n                'android_vr',\n"
_YOUTUBE_NEW = ("('auth_enabled|no_kids|av1|vp9.2|avc1|surround_sound', (\n"
                "                # 'android_vr',  # disabled by script.papa.inicio: GVS 403"
                " (plugin.video.youtube issue 1483)\n")

# Arctic Fuse 3: las filas de carátulas (grupo 500 de Includes_Hubs.xml) desaparecen del todo, despacio y con
# curva suave, mientras suena nuestro tráiler, y vuelven igual de suaves al tocar el mando (System.IdleTime a 0).
AF3_FILE = '1080i/Includes_Hubs.xml'
TRAILER_PROPERTY = 'papa.trailer'
ROWS_FADE = ('<animation effect="fade" start="100" end="0" time="1500" tween="sine" easing="inout" '
             'condition="String.IsEqual(Window(Home).Property(%s),1) + System.IdleTime(3) '
             '+ !Window.IsActive(fullscreenvideo)">Conditional</animation><!-- %s -->' % (TRAILER_PROPERTY, MARK))
_ROWS_GROUP = re.compile(r'^([ \t]*)<control type="group" id="500">\n([ \t]*)', re.M)
_OUR_LINES = re.compile(r'^[ \t]*<animation [^\n]*<!-- %s -->\n' % re.escape(MARK), re.M)


# Arctic Fuse 3 se actualiza sola y deja el archivo de las filas como venía, y Kodi recarga la skin sin el fundido.
# El servicio lo vuelve a arreglar cada poco y recarga la skin cuando nadie está usando Kodi.
CHECK_EVERY = 10 * 60.0
QUIET = '!Player.HasMedia + !System.HasActiveModalDialog + System.IdleTime(300)'


class PatchKeeper(object):
    """apply() aplica los arreglos que falten y devuelve los addons tocados; reload_skin() recarga la skin."""

    def __init__(self, apply, cond, reload_skin, clock, skin):
        self.apply, self.cond, self.reload_skin, self.clock, self.skin = apply, cond, reload_skin, clock, skin
        self.next_check, self.reload_pending = 0.0, False

    def tick(self):
        now = self.clock()
        if now >= self.next_check:
            self.next_check = now + CHECK_EVERY
            if self.skin in self.apply():
                self.reload_pending = True  # Kodi ya tiene cargada la skin sin el arreglo
        if self.reload_pending and self.cond(QUIET):
            self.reload_pending = False
            self.reload_skin()


def youtube_needs_patch(version):
    return version in YOUTUBE_BROKEN


def patch_youtube(text):
    if text.count(_YOUTUBE_OLD) != 1:
        return None
    return text.replace(_YOUTUBE_OLD, _YOUTUBE_NEW)


def patch_af3_rows(text):
    clean = _OUR_LINES.sub('', text)  # quita un fundido nuestro de otra versión
    if not _ROWS_GROUP.search(clean):
        return None
    # La animación va como primer hijo del grupo, con la sangría de sus hijos.
    new = _ROWS_GROUP.sub(lambda m: '%s<control type="group" id="500">\n%s%s\n%s' % (
        m.group(1), m.group(2), ROWS_FADE, m.group(2)), clean)
    return None if new == text else new
