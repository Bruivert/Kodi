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


# Arctic Fuse 3: la 1.0.12 cambió la acción de la lupa por la búsqueda del asistente. Desde la 1.0.13 la lupa vuelve a
# abrir la búsqueda de AF3, con Películas y Series del catálogo de Palantir como fuentes (menus.SEARCH_WIDGETS): esto
# deshace aquel cambio en las cajas que lo tienen.
AF3_HOME_FILE = '1080i/Includes_Home.xml'
OUR_SEARCH_ACTION = '<param name="action">RunScript(%s,buscar)</param>' % MARK
AF3_SEARCH_ACTION = ('<param name="action">RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,'
                     'progress_dialog$VAR[Value_MultiSearch_Layout_Param]$VAR[Value_MultiSearch_Discover_Param])'
                     '</param>')

# Textos de la búsqueda que AF3 y skinvariables no traen en español: id → (msgid, msgstr), tal como van en el .po.
AF3_STRINGS_FILE = 'language/resource.language.es_es/strings.po'
AF3_STRINGS = {31850: ('Results', 'Resultados'), 31851: ('Sources', 'Fuentes'), 31852: ('Decade', 'Década'),
               31861: ('No results', 'Sin resultados'), 31863: ('Search for', 'Busca'),
               31864: ('movies, TV shows, people and more', 'películas y series'),
               31865: ('Enter a search term to begin.', 'Escribe lo que quieres ver.')}
SKINVARIABLES_STRINGS_FILE = 'resources/language/resource.language.es_es/strings.po'
SKINVARIABLES_STRINGS = {32099: ('Decade', 'Década'), 32100: ('Any', 'Todos'),
                         32104: ('Searching \\"{}\\"', 'Buscando «{}»')}


# Arctic Fuse 3: en las tarjetas de un capítulo usa su miniatura solo si es distinta de la carátula. Palantir pone la
# foto del capítulo (still) en las dos y AF3 pintaba el fondo de la serie, el mismo en todos los capítulos. Delante de
# cada una de esas reglas (106 en 3.5.4, una por lista y contenedor) va otra que usa la foto del capítulo.
AF3_IMAGES_FILE = '1080i/script-skinvariables-images-includes.xml'
_EPISODE_THUMB = re.compile(r'^([ \t]*)(<value condition="\[String\.IsEqual\((?P<li>.+?)\.DBType,episode\) \| '
                            r'String\.IsEqual\((?P=li)\.DBType,video\)[^\n]*?">\$INFO\[(?P=li)\.Art\(thumb\)\]</value>)',
                            re.M)
STILL_RULE = ('<value condition="String.IsEqual({li}.DBType,episode) + !String.IsEmpty({li}.Art(still)) + '
              '!String.IsEqual({li}.Icon,OverlaySpoiler.png)">$INFO[{li}.Art(still)]</value>')  # sin destripar
_OUR_STILL = re.compile(r'\.Art\(still\)\) \+ !String\.IsEqual\([^"]*?\.Icon,OverlaySpoiler\.png\)">')

# Balandro: mínimo 1080p al reproducir películas (decisión del usuario, 23/11/2026). Balandro solo ordena los enlaces
# por calidad; esto descarta los que no dicen 1080p/4K (calidad.HD), también los que no dicen nada. Los capítulos no se
# tocan: las webs en castellano no dan su calidad y el asistente los filtra por tamaño (calidad.episode_hd).
BALANDRO_FILE = 'platformcode/platformtools.py'
_BALANDRO_SORT = '    itemlist = servertools.filter_and_sort_by_quality(itemlist)\n'
BALANDRO_MIN = ("    itemlist = [it for it in itemlist if parent_item.contentType == 'episode' or "
                "re.search(r'1080|2160|\\b4k\\b|uhd|full ?hd', it.quality or '', re.I)]  # %s: 1080p\n" % MARK)


# Balandro 4.0.34: DonTorrent cambió su página de resultados (23/11/2026): los enlaces van con comillas dobles y la
# lista acaba en </ul>, y la búsqueda de Balandro no encontraba nada. Se aceptan las dos formas.
DONTORRENTS_FILE = 'channels/dontorrents.py'
_DT_OLD = ("    bloque = scrapertools.find_single_match(data, '>Resultados<(.*?)</nav>')\n\n"
           "    patron = \"<a href='(.*?)'.*?\"\n"
           "    patron += 'class=\"text-decoration-none\">(.*?)</a>'\n")
_DT_NEW = ("    bloque = scrapertools.find_single_match(data, '>Resultados<(.*?)(?:</nav>|</ul>)')  # %s\n\n"
           "    patron = \"<a href=[\\\"'](.*?)[\\\"'][^>]*?\"\n"
           "    patron += 'class=\"[^\"]*text-decoration-none\">(.*?)</a>'\n" % MARK)


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


def patch_af3_search(text):
    if text.count(OUR_SEARCH_ACTION) != 1:
        return None  # AF3 como viene, u otra skin
    return text.replace(OUR_SEARCH_ACTION, AF3_SEARCH_ACTION)


def add_strings(text, strings):
    """Pone en un strings.po las traducciones que faltan (o tienen msgstr vacío); las que ya están no se tocan."""
    new = text or ''
    for sid in sorted(strings):
        msgid, msgstr = strings[sid]
        found = re.search(r'(msgctxt "#%d"\n(?:#[^\n]*\n)*msgid "(?:[^"\\]|\\.)*"\n)msgstr "((?:[^"\\]|\\.)*)"' % sid, new)
        if found:
            if not found.group(2):
                new = new[:found.start()] + found.group(1) + 'msgstr "%s"' % msgstr + new[found.end():]
        elif 'msgctxt "#%d"' % sid not in new:  # otro formato (msgid en varias líneas): mejor no duplicarlo
            new = (new.rstrip('\n') + '\n\n' if new else '') + 'msgctxt "#%d"\nmsgid "%s"\nmsgstr "%s"\n' % (
                sid, msgid, msgstr)
    return None if new == (text or '') else new


def patch_af3_strings(text):
    return add_strings(text, AF3_STRINGS)


def patch_skinvariables_strings(text):
    return add_strings(text, SKINVARIABLES_STRINGS)


def patch_af3_episode_thumbs(text):
    if _OUR_STILL.search(text):
        return None  # ya aplicado
    new, count = _EPISODE_THUMB.subn(
        lambda m: '%s%s\n%s%s' % (m.group(1), STILL_RULE.format(li=m.group('li')), m.group(1), m.group(2)), text)
    return new if count else None


def patch_balandro_quality(text):
    if BALANDRO_MIN in text or text.count(_BALANDRO_SORT) != 1:
        return None  # ya aplicado, u otra versión de Balandro
    return text.replace(_BALANDRO_SORT, _BALANDRO_SORT + BALANDRO_MIN)


def patch_dontorrents_search(text):
    if text.count(_DT_OLD) != 1:
        return None  # ya aplicado, u otra versión
    return text.replace(_DT_OLD, _DT_NEW)


# --- plugin.video.telegram: el tema del foro de cada vídeo (permiso del usuario, 24/11/2026) -------------------
# Su API (api/media) no dice de qué tema (Películas, Series, Chat…) es cada mensaje; el asistente lo necesita para
# la actualización nocturna del catálogo (telegram.py). Se añade el campo «topic» (0 si no es de un tema).
TELEGRAM_FILE = 'resources/lib/tgkodi/server.py'
_TG_OLD = '        "ext": ".jpg",\n    }\n'
_TG_NEW = ('        "ext": ".jpg",\n'
           '        "topic": ((m.reply_to.reply_to_top_id or m.reply_to.reply_to_msg_id)  # papa: tema del foro\n'
           '                  if getattr(m.reply_to, "forum_topic", False) else 0),\n'
           '    }\n')


def patch_telegram_topic(text):
    if text.count(_TG_OLD) != 1 or 'papa: tema del foro' in text:
        return None  # ya aplicado, u otra versión
    return text.replace(_TG_OLD, _TG_NEW)
