# Kodi de Papá — Guía de instalación

Esta guía deja la Vontar X4 (Kodi 21 Omega) con un menú sencillo, estilo Apple TV:

**Inicio · Películas · Series · Favoritos · Deportes**

- Películas, Series y Novedades salen de **Palantir** (con tu AllDebrid).
- Deportes sale de **BlackGhost**. Filas: Agenda de hoy (en hora de España), Partidos en España (Acestream), Fútbol, Motor (F1 y MotoGP) y Canales Acestream. Con los botones bajo el menú se llega además a Baloncesto, NFL, Fórmula 1 en español (repeticiones) y UFC y boxeo. BlackGhost no tiene pádel.
- Nota de **IMDb** en películas y series.
- **Tráileres automáticos en español de España**: si tu padre se queda unos segundos sobre una película, suena su tráiler de fondo. Si no hay ninguno en castellano, suena el de la web de TMDb en el idioma original (casi siempre inglés), como cuando miras la película en el móvil.

> Antes de empezar, Palantir (con AllDebrid) y BlackGhost tienen que estar instalados y funcionando en la caja.

---

## 1. Una sola vez, en GitHub (desde el Mac)

1. Abre `github.com/Bruivert/Kodi` → **Settings** → **General** → al final, **Change visibility** → **Public**.
   (En el repositorio solo hay configuración. Ni tu AllDebrid ni el código de BlackGhost están ahí.)
2. **Settings** → **Pages** → *Build and deployment* → **Deploy from a branch** → rama **main**, carpeta **/docs** → **Save**.
3. Espera un par de minutos y abre `https://bruivert.github.io/Kodi/`. Tiene que salir un enlace a `repository.papa-1.0.0.zip`.

## 2. Dos claves gratuitas y el móvil como teclado

- **OMDb** (para la nota de IMDb): en `omdbapi.com/apikey.aspx` elige **FREE**, pon tu correo y activa la clave con el enlace que te llega.
- **TMDb** (para los tráileres): crea una cuenta en `themoviedb.org` → **Ajustes** → **API** → solicita una clave de tipo *Developer*. Usa la **Clave de API (v3)**.
- Para no escribir las claves con el mando, instala en el móvil **Kore** (Android) u **Official Kodi Remote** (iPhone).
  En la caja activa: **Ajustes → Servicios → Control → Permitir el control remoto por HTTP**.
  Cuando Kodi muestre un teclado en pantalla, escribe desde el móvil.

## 3. En la Vontar, con el mando

1. **Ajustes → Sistema → Addons → Orígenes desconocidos**: actívalo.
2. **Ajustes → Explorador de archivos → Añadir fuente → \<Ninguno\>**. Escribe `https://bruivert.github.io/Kodi/` y ponle de nombre `papa`.
3. **Addons → Instalar desde un archivo zip → papa → repository.papa-1.0.0.zip**.
4. **Addons → Instalar desde repositorio → Repo Kodi de Papá → Addons de programas → Kodi de Papá — Asistente → Instalar**.
5. **Addons → Addons de programas → Kodi de Papá — Asistente → Configurar todo**. El asistente:
   - Pregunta si instalar **Arctic Fuse 3** y **YouTube** → **Sí** a los dos.
   - Pide las claves de **OMDb** y de **TMDb**. Puedes dejarlas vacías y ponerlas después.
   - Te pide las claves y el **código de BlackGhost** (sale en su Telegram, p. ej. `n17`). El asistente se lo deja guardado a BlackGhost, que ya no lo vuelve a pedir.
   - Recorre Palantir y BlackGhost. Si no reconoce alguna carpeta, te pregunta cuál es. Si no existe, elige **«— No está / saltar —»**.
   - Te enseña un resumen de lo que ha encontrado.
   - Cambia la skin. Cuando Kodi pregunte **«¿Mantener este cambio?»**, pulsa **Sí**.
   - Espera unos segundos en el Inicio hasta que salga **«Menú de papá listo»**.

## 4. Chuleta para tu padre

| Quiero… | Hago… |
|---|---|
| Moverme | Flechas del mando |
| Ver algo | **OK** |
| Volver | **Atrás** |
| Buscar una película o serie | La **lupa** del menú → escribe el título con las letras de la pantalla (pulsando la barra sale el teclado completo; también se puede escribir desde el móvil). Salen dos filas, **Películas** y **Series** → elige y **OK**: Palantir enseña sus enlaces o las temporadas, como siempre. **Atrás** vuelve a la búsqueda. |
| Guardarlo en Favoritos | Mantener pulsado **OK** (o el botón ☰) → **Añadir a favoritos** |
| Ver mis favoritos | La sección **Favoritos** o la última fila del Inicio, **Mis favoritos**. Las películas y series salen con su fanart de fondo, como en Películas. |

## 5. Mantenimiento (abre el asistente)

- **Actualizar menús**: úsalo si Palantir o BlackGhost cambian sus secciones.
- **Tráileres automáticos: Sí/No**: los enciende o los apaga.
- **Claves de OMDb y TMDb**: para cambiarlas o ponerlas más tarde.
- **Diagnóstico**: crea `informe-kodi.txt` y lo guarda en el pendrive si hay uno conectado (o en *Descargas* de la caja). Mándamelo:
  así puedo automatizar el código de BlackGhost y arreglar lo que falle. Solo lleva nombres y rutas. Las claves y los códigos salen tapados con `***`.

## 6. Si algo falla

| Problema | Solución |
|---|---|
| No sale la nota de IMDb | Revisa la clave de OMDb (asistente → Claves). |
| No hay tráileres | Revisa la clave de TMDb. Si YouTube pide claves propias, configúralas en los ajustes de YouTube. Algunas películas no tienen tráiler de España: es normal. |
| El tráiler se corta a los pocos segundos | Era un fallo del addon de YouTube 7.4.4 (YouTube corta los vídeos que pide con su cliente «android_vr»). El asistente lo desactiva en ese archivo del addon (guarda el original en `addon_data/script.papa.inicio/backup/`) y lo vuelve a hacer si YouTube se reinstala. Si aun así alguno se atasca, se para solo y no se repite; con 3 seguidos, los tráileres descansan media hora. |
| Las carátulas desaparecen mientras suena el tráiler | Es a propósito: a los 3 segundos de tráiler se desvanecen despacio para que se vea entero, y vuelven al tocar cualquier botón. El asistente lo añade a la skin (con copia del original). Arctic Fuse 3 se actualiza sola y lo quita: el asistente lo comprueba cada 10 minutos, lo vuelve a poner y recarga la skin cuando nadie usa Kodi (nada sonando y 5 minutos sin tocar el mando). |
| El tráiler tarda en salir | Debería sonar unos 4 segundos después de pararte en una película. Antes tardaba 15-20 s porque, al acabar cada tráiler, Kodi recargaba las filas de Palantir; el asistente les pone un orden fijo para que no lo haga y, si ya tenías el menú montado, lo rehace solo al reiniciar Kodi. Tras encender la caja, el primero puede tardar algo más. |
| Un tráiler suena en inglés | YouTube añade a muchos tráileres españoles un doblaje automático al inglés y lo elegía porque venía configurado en inglés. El asistente lo pone en español de España (idioma `es`, región `ES`). Además, antes de poner un tráiler mira su título en YouTube y se salta los subtitulados (VOSE) y los que TMDb marca como españoles pero son en inglés. |
| Una película no tiene tráiler | Si TMDb no tiene un tráiler en español de España, el asistente lo busca en YouTube (título y año de la película + «tráiler español») y solo acepta uno que empiece por el título, diga que es en español o venga de un canal de España, dure menos de 5 minutos y no sea latino ni subtitulado. Si no lo encuentra, pone el teaser en español de TMDb. Y si tampoco hay, el vídeo de TMDb en el idioma original de la película (el tráiler; si no hay, el teaser o un clip), igual que la web de TMDb: así salen, por ejemplo, «Ali G: Kién es yo?» (en inglés) o «El regalo de cumpleaños» (un clip en alemán). Solo se queda sin tráiler lo que TMDb no tiene en ningún idioma. |
| Palantir pregunta por Trakt.tv o una fila sale vacía | Algunas listas de Palantir («Más vistas», «Recomendadas», «Series en seguimiento») solo funcionan con una cuenta de Trakt.tv. El menú no las usa: Películas lleva **Estrenos**, **Recién añadidas** y **Géneros**, y Series **Nuevos episodios**, **Nuevas series** y **Géneros**. Si aun así sale la pregunta, responde **No** y haz Asistente → **Actualizar menús**. |
| Una fila tarda en salir o no está al día | Las filas de Palantir y de Deportes salen de una copia que el asistente renueva sola (cada hora las películas y series, cada 15 min los deportes; empieza 2 min después de encender y cuando nadie toca el mando). Arctic Fuse 3 vuelve a pedir todas las filas cada vez que se entra en una sección y Kodi ejecuta los addons de Python de uno en uno: pedírselas cada vez a Palantir hacía esperar más de un minuto. En el primer minuto tras encender sigue yendo algo más lento (arrancan a la vez los servicios de otros addons). |
| Un partido sale con un fondo que no le toca | BlackGhost no trae imágenes: el asistente pone las de TheSportsDB. Si el partido nombra su competición (Liga de Naciones, Champions, LaLiga, NBA…), la de la competición; si no, la del deporte (tenis, baloncesto, motor…), y si no se sabe, la de fútbol. Las de las competiciones se descargan poco a poco (su clave gratuita deja muy pocas consultas) y se guardan una semana. |
| Deportes vacío o con error | Seguramente ha caducado el código de BlackGhost (va dentro de las rutas de Deportes). Pon el nuevo en **Asistente → Claves** (o en sus ajustes, «Código de BlackGhost»): el asistente se lo pasa a BlackGhost, vuelve a buscar las filas y rehace el menú solo. |
| La lupa no encuentra una película o serie | Sale «Sin resultados». Busca dentro del título que enseña Palantir (en español y, a veces, el original entre paréntesis), sin mirar acentos ni mayúsculas, y a partir de 2 letras: prueba con una sola palabra del título. Encuentra lo mismo que «Buscar: Por título» de Palantir, pero sin abrirlo: tarda unos 3 segundos en vez de más de 20. |
| El menú no ha cambiado | Reinicia Kodi. El servicio termina de montarlo al volver al Inicio. |
| Falta una sección | Asistente → **Actualizar menús**. Si el addon no está instalado, su sección se oculta. |
