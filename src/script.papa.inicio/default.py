# -*- coding: utf-8 -*-
"""Asistente: lo usa el hijo, no el padre."""
import sys

import xbmc
import xbmcgui

from resources.lib import kodi_setup as ks

SEARCH = ('RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,progress_dialog,mediatype_lists,'
          'no_all_list,no_discover)')


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
    ks.apply_patches()  # tráileres sin cortes y filas que se atenúan mientras suenan
    ks.apply_youtube_settings()  # pista española y vídeo directo de Google (el siguiente tráiler sin esperas)
    ks.ensure_spanish()
    ks.ask_keys()
    ks.apply_tmdbhelper()
    rutas = ks.run_discovery()
    dialog.ok(ks.TITLE, 'Esto es lo que he encontrado:\n' + ks.summary(rutas))
    ks.set_pending(True)
    if ks.finish_pending():
        dialog.ok(ks.TITLE, 'Listo. Vuelve al Inicio para ver el nuevo menú.')
        return
    if xbmc.getSkinDir() == ks.SKIN:
        # Arctic Fuse 3 ya está puesta pero no ha terminado de arrancar: el servicio lo monta en cuanto pueda.
        dialog.ok(ks.TITLE, 'El menú se terminará de montar solo en unos segundos. '
                            'Si no aparece, reinicia Kodi.')
        return
    dialog.ok(ks.TITLE, 'Ahora Kodi cambiará a la nueva skin. Cuando pregunte si quieres mantenerla, '
                        'pulsa «Sí». Luego espera unos segundos: el menú se monta solo.')
    ks.set_skin(ks.SKIN)


def actualizar_menus():
    rutas = ks.run_discovery()
    xbmcgui.Dialog().ok(ks.TITLE, ks.summary(rutas))
    ks.set_pending(True)
    ks.finish_pending()  # si Arctic Fuse 3 aún no está lista, lo termina el servicio


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
    if len(sys.argv) > 1 and sys.argv[1] == 'buscar':
        # La lupa de la 1.0.12, hasta que la skin se recarga sin aquel parche: la búsqueda de AF3 como la abre la lupa.
        xbmc.executebuiltin(SEARCH)
    else:
        main()
