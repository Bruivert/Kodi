# La lupa con la búsqueda de Arctic Fuse 3 y el catálogo de Palantir — diseño (1.0.13)

18/11/2026. Sustituye a la lupa de la 1.0.12 (teclado propio → «Películas / Series» → «Por título» de Palantir escrito solo).

## Qué y por qué

El usuario quiere **la misma función** que ahora: buscar por título las películas y series de Palantir, elegir una y que se vea. Pero que se vea **como el resto de la skin**, en vez de una sucesión de ventanas sueltas: teclado, lista, segundo teclado que se escribe solo, «Cargando» y la carpeta de Palantir empezando en «..».

**Objetivos**
- La lupa abre la pantalla de búsqueda propia de Arctic Fuse 3: barra arriba, letras en pantalla, filtros y una fila de resultados por tipo con el fondo, el logo y la sinopsis de la skin.
- Dos filas, **Películas** y **Series**, con los mismos títulos que encuentra «Por título» de Palantir.
- Al elegir uno, Palantir hace lo de siempre: su lista de enlaces y la reproducción en películas, las temporadas en series.
- **Rápido**: los resultados en 1–2 s desde que se deja de escribir. El usuario rechazó 23 s («totalmente inaceptable»).
- Todo en español. Los filtros (Fuentes, Contenido, Reiniciar, Ordenar por, Género, Década) **se quedan, traducidos** (decisión del usuario).

**Fuera de alcance**
- Otras fuentes: biblioteca de Kodi, música, TMDb, «Descubrir».
- Las marcas de visto y el progreso en los resultados: Palantir las pone en su lista; aquí no, de momento.
- El ajuste «autoplay 1080» de Palantir: es del usuario y no se toca.

**Lo que sería un fracaso aunque funcione**
- Que buscar tarde más de 2–3 s.
- Que encuentre cosas distintas de las que encuentra Palantir.
- Tocar los archivos o la base de Palantir: solo se lee.

## Lo comprobado en la caja (prueba desechable, 18/11/2026)

- La pantalla de búsqueda de AF3 (skinvariables `run_multisearch`) admite como fuente cualquier ruta con `{query}`. Las fuentes se leen de `skinvariables-shortcut-searchwidgets.json`.
  - Con dos fuentes del asistente salen «Películas (n)» y «Series (n)» con carátula, logo, sinopsis, nota de IMDb y fondo.
  - Si un tipo no tiene resultados, no sale su fila. Con «ballena» solo sale «Películas (4)».
- Elegir funciona. *The Pitt* abre sus temporadas, y *Los misterios de Pittsburgh* y *La ballena* se reproducen. Al parar o con Atrás se vuelve a la búsqueda.
- **Tiempos**:
  - Palantir tarda 4–4,5 s en arrancar en cada llamada, aunque solo devuelva su menú. Pedirle las dos búsquedas por JSON-RPC sumó 23 s.
  - El asistente contesta en 0,7–1,7 s.
  - Buscando directamente en la base de Palantir: leer los títulos 0,48 s, normalizarlos 0,68 s, cada búsqueda 0,03–0,05 s y las fichas 0,003 s.
  - Los resultados coinciden con los de Palantir: «pitt» 1 + 1, «ballena» 4 + 0, «allen» 9 películas.
- **Fichas montadas por el asistente**, sin pasar por la búsqueda de Palantir:
  - La serie (`listado_temporadaS`) abre «Temporada 1» y «Temporada 2».
  - La película (`selectvideos_`) saca la lista de enlaces de Palantir y reproduce en 1080p.

## Enfoques

1. **Búsqueda de la skin + pedirle la búsqueda a Palantir** (la prueba): funciona, pero tarda 23 s. Descartado por el usuario.
2. **Búsqueda de la skin + leer el catálogo de Palantir directamente** (elegido): menos de 2 s y los mismos resultados. A cambio, depende de cómo guarda Palantir su base y sus fichas. Palantir ya no se actualiza (su repositorio da 404), así que el riesgo es bajo. Si cambiara, la lupa dejaría de encontrar y se notaría enseguida.
3. **Pulir la lupa de la 1.0.12** (plan B): quitar «..», poner un título y mejorar el selector. Siguen los dos teclados y las ventanas sueltas. No hace falta.

## Cómo se hace

### 1. La lupa vuelve a ser la de AF3
- `patches.patch_af3_search` pasa a **deshacer** el cambio de la 1.0.12: devuelve `RunScript(script.papa.inicio,buscar)` a la acción original de AF3:
  `RunScript(script.skinvariables,run_multisearch,tmdbhelper_container,progress_dialog$VAR[Value_MultiSearch_Layout_Param]$VAR[Value_MultiSearch_Discover_Param])`
  Con un AF3 sin parchear no hace nada.
- En `menus.skin_builtins`: `Skin.SetBool(HomeSwitcher.Search.DisableDiscover)`, para que no añada filas «Descubrir» de TMDb (no se pueden reproducir). Se deja `HomeSwitcher.Search.Combined` sin poner: una fila por tipo.

### 2. Las fuentes de búsqueda
- `menus.build_preset` añade `skinvariables-shortcut-searchwidgets.json` con dos entradas, ambas con `target` `videos` y `widget_style` `Poster`:
  - Películas: `plugin://script.papa.inicio/?buscar=peliculas&q={query}`
  - Series: `plugin://script.papa.inicio/?buscar=series&q={query}`
- `copy_menufolder` copia todos los `.json` de la carpeta, así que va con el resto del menú. `MENU_VERSION` 10.

### 3. Buscar en el catálogo (`resources/lib/catalogo.py`, puro; `plugin.py` lo une a Kodi)
- **La base**: `special://home/addons/plugin.video.palantir3/moria.cm3` si existe; si no, `special://profile/addon_data/script.module/settings.xml`. Es la misma lógica que `MoriaDB` de Palantir. Se abre en solo lectura (`file:…?mode=ro`).
- **Índice propio** en `addon_data/script.papa.inicio/catalogo.db`: tipo, tmdb y título normalizado.
  - Entran los mismos títulos que en «Por título» de Palantir: películas de categoría «Película» y series «General», «Retro» y «Reality». En ambos casos, solo con enlaces (`EXISTS` en `enlaces_pelis` / `enlaces_series`, como sus vistas).
  - Se rehace cuando cambian la fecha o el tamaño de la base de Palantir: ~1,2 s una sola vez. Se guardan en el propio índice.
- **Normalizar** igual que `map_string` de Palantir (minúsculas, sin acentos): comprobar su código al hacerlo, para que «pelicula» encuentre «Película» igual que allí.
- **Buscar**: el texto normalizado como subcadena (`LIKE`) en el índice.
  - Menos de 2 letras: lista vacía. Así no se recorre medio catálogo mientras se escribe.
  - Hasta 60 por fila, primero los que empiezan por el texto y luego por orden alfabético.
- **Fichas**: `titulo, fecha, plot, poster, fondo, duration, mpaa, genero, trailer, clearlogo, rating` de `pelis` / `series` por tmdb.
- **Ruta de cada elemento**: la ficha de Palantir (dict con claves ordenadas, `'{"k": repr(v), …}'`, codificada como su `p3b64encode`):
  - película: `action: selectvideos_`, `content: movies`, `isPlayable: True`;
  - serie: `action: listado_temporadaS`, `content: tvshows`;
  - con `title`/`tvshowtitle`, `label`, `tmdb`, `fecha`, `plot`, `poster`, `fanart`, `clearlogo`, `mpaa`, `rating`, `duration`.
  - Película: no es carpeta y lleva `IsPlayable=true`. Serie: carpeta.
- **ListItem**:
  - Etiqueta: el título limpio, sin los colores de Palantir.
  - Imágenes como `getart` de Palantir: prefijo `https://image.tmdb.org/t/p/`, carátula w500, fondo w1280 y logo w500.
  - Info con título, año, sinopsis, nota, géneros, duración, edad, tráiler y `mediatype` movie/tvshow.
  - `uniqueid` tmdb, para que la skin y TMDb Helper pongan logo y nota de IMDb como ya hacen con Favoritos.
- No hay candado ni marca `p3_play`: Palantir no interviene hasta que se elige un resultado.

### 4. Textos en español (parche, como los demás; se reaplica si el addon se actualiza)
- **AF3**, `language/resource.language.es_es/strings.po`, se añaden si faltan:

  | Id | Inglés | Español |
  |---|---|---|
  | 31850 | Results | Resultados |
  | 31851 | Sources | Fuentes |
  | 31852 | Decade | Década |
  | 31861 | No results | Sin resultados |
  | 31863 | Search for | Busca |
  | 31864 | movies, TV shows, people and more | películas y series |
  | 31865 | Enter a search term to begin. | Escribe lo que quieres ver. |

- **skinvariables**, `resources/language/resource.language.es_es/strings.po`:

  | Id | Inglés | Español |
  |---|---|---|
  | 32099 | Decade | Década |
  | 32100 | Any | Todos |
  | 32104 | Searching "{}" | Buscando «{}» |

- Los textos de la skin se ven tras recargarla. La recarga ya la hace `PatchKeeper` cuando nadie usa Kodi.

### 5. Se retira la lupa de la 1.0.12
- Se borran `resources/lib/buscar.py` y `tests/test_buscar.py`, y la entrada `buscar` de `default.py`.
- `discover` deja de guardar «Por título» (`rutas['palantir']['buscar']`): ya no hace falta.

## Comprobación en la caja
1. Lupa → pantalla de búsqueda de AF3 en español.
2. «pitt» → Películas (1) y Series (1) en 1–2 s. «ballena» → solo Películas (4). Un texto sin resultados → «Sin resultados».
3. Elegir película → enlaces de Palantir → se reproduce. Al parar se vuelve a la búsqueda.
4. Elegir serie → temporadas; Atrás → búsqueda.
5. Escribir con las letras en pantalla, con el teclado completo (pulsando la barra) y desde el móvil.
6. Medir y anotar los tiempos.

## Lo que decide quien lo programe
- El formato exacto del índice.
- El orden fino de los resultados.
- El límite de 60.
- Cómo se detecta que la base de Palantir ha cambiado.

## Cambios tras medir en la caja (implementación)

- **Una sola fuente**, «Películas y series» (`?buscar=todo`), en vez de dos. Cada fuente es una llamada al asistente, y arrancarlo cuesta 0,7–1,5 s mientras que la búsqueda tarda 0,03–0,07 s. La pantalla de AF3 reparte igual los resultados en las filas «Películas» y «Series».
- **El índice lo prepara el servicio** (`IndexKeeper`, a los 60 s de arrancar y cada 10 min si cambia la base). La primera búsqueda tras instalar tardaba 8 s porque las dos filas lo creaban a la vez.
- **Tiempos finales** (18/11/2026), de aceptar el teclado hasta ver las filas: 3,2–3,8 s.
  - El asistente busca en 0,1–0,4 s; el resto es el arranque de Python de Kodi y skinvariables.
  - Con las letras de la pantalla, la fila sale ~1,2 s después de la última letra.

