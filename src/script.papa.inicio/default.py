# -*- coding: utf-8 -*-
"""Asistente: lo usa el hijo, no el padre."""
import xbmc
import xbmcgui

from resources.lib import kodi_setup as ks


def configurar_todo():
    dialog = xbmcgui.Dialog()
    if not dialog.yesno(ks.TITLE, 'Se instalará Arctic Fuse 3 y se montará el menú de tu padre '
                                  '(Películas, Series, Novedades, Deportes y Favoritos). ¿Seguimos?'):
        return
    ks.notify('Instalando Arctic Fuse 3…')
    if not ks.ensure_addon(ks.SKIN):
        dialog.ok(ks.TITLE, 'No se pudo instalar Arctic Fuse 3. Comprueba que tienes instalado el '
                            '"Repo Kodi de Papá" y que hay internet, y vuelve a intentarlo.')
        return
    if not ks.ensure_addon(ks.YOUTUBE, timeout=300):
        dialog.ok(ks.TITLE, 'No se instaló YouTube: sin él no habrá tráileres. Lo demás sigue igual.')
    ks.ensure_spanish()
    ks.ask_keys()
    ks.apply_tmdbhelper()
    rutas = ks.run_discovery()
    dialog.ok(ks.TITLE, 'Esto es lo que he encontrado:\n' + ks.summary(rutas))
    ks.set_pending(True)
    if ks.af3_ready():
        ks.apply_skin_config()
        ks.set_pending(False)
        dialog.ok(ks.TITLE, 'Listo. Vuelve al Inicio para ver el nuevo menú.')
        return
    dialog.ok(ks.TITLE, 'Ahora Kodi cambiará a la nueva skin. Cuando pregunte si quieres mantenerla, '
                        'pulsa «Sí». Luego espera unos segundos en el Inicio: el menú se monta solo.')
    ks.set_skin(ks.SKIN)


def actualizar_menus():
    rutas = ks.run_discovery()
    xbmcgui.Dialog().ok(ks.TITLE, ks.summary(rutas))
    if ks.af3_ready():
        ks.apply_skin_config()
        ks.notify('Menú actualizado')
    else:
        ks.set_pending(True)


def cambiar_trailers():
    activo = ks.setting('trailers_auto') != 'false'
    ks.set_setting('trailers_auto', 'false' if activo else 'true')
    ks.notify('Tráileres automáticos: %s' % ('NO' if activo else 'SÍ'))


def claves():
    ks.ask_keys()
    ks.apply_tmdbhelper()
    ks.notify('Claves guardadas')


def main():
    while not xbmc.Monitor().abortRequested():
        trailers = 'Sí' if ks.setting('trailers_auto') != 'false' else 'No'
        opciones = [
            ('Configurar todo', configurar_todo),
            ('Actualizar menús (si Palantir o BlackGhost cambian)', actualizar_menus),
            ('Tráileres automáticos: %s' % trailers, cambiar_trailers),
            ('Claves de OMDb y TMDb', claves),
            ('Diagnóstico (informe para soporte)', ks.run_diagnostico),
        ]
        idx = xbmcgui.Dialog().select(ks.TITLE, [o[0] for o in opciones])
        if idx < 0:
            return
        opciones[idx][1]()


if __name__ == '__main__':
    main()
