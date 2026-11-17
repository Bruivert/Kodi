# Kodi de Papá — Guía de instalación

Esta guía deja la Vontar X4 (Kodi 21 Omega) con un menú sencillo, estilo Apple TV:

**Inicio · Películas · Series · Novedades · Deportes · Favoritos**

- Películas, Series y Novedades salen de **Palantir** (con tu AllDebrid).
- Deportes sale de **BlackGhost**: Agenda de hoy, Fútbol, Baloncesto, NFL, Pádel, Fórmula 1, MotoGP y UFC.
- Nota de **IMDb** en películas y series.
- **Tráileres automáticos en español de España**: si tu padre se queda unos segundos sobre una película, suena su tráiler de fondo. Si no hay tráiler de España, no suena nada.

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
   - Recorre Palantir y BlackGhost. Si **BlackGhost pide el código**, escríbelo. Si no reconoce alguna carpeta, te pregunta cuál es. Si no existe, elige **«— No está / saltar —»**.
   - Te enseña un resumen de lo que ha encontrado.
   - Cambia la skin. Cuando Kodi pregunte **«¿Mantener este cambio?»**, pulsa **Sí**.
   - Espera unos segundos en el Inicio hasta que salga **«Menú de papá listo»**.

## 4. Chuleta para tu padre

| Quiero… | Hago… |
|---|---|
| Moverme | Flechas del mando |
| Ver algo | **OK** |
| Volver | **Atrás** |
| Guardarlo en Favoritos | Mantener pulsado **OK** (o el botón ☰) → **Añadir a favoritos** |
| Ver mis favoritos | Sección **Favoritos** o la fila **Mis favoritos** del Inicio |

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
| El tráiler se corta a los pocos segundos | Era un fallo del addon de YouTube 7.4.4 (YouTube corta los vídeos que pide con su cliente «android_vr»). El asistente lo desactiva en ese archivo del addon (guarda el original en `addon_data/script.papa.inicio/backup/`) y lo vuelve a hacer si YouTube se reinstala. Si aun así alguno se atasca, se para solo y no se repite; con 3 seguidos, los tráileres descansan hasta que reinicies Kodi. |
| Las carátulas se atenúan mientras suena el tráiler | Es a propósito: así se ve el tráiler. Vuelven al tocar cualquier botón. El asistente lo añade a la skin (con copia del original) y lo repone tras cada actualización de Arctic Fuse 3, al reiniciar Kodi. |
| Deportes vacío o con error | Seguramente ha caducado el código de BlackGhost: ábrelo una vez y pon el nuevo. |
| El menú no ha cambiado | Reinicia Kodi. El servicio termina de montarlo al volver al Inicio. |
| Falta una sección | Asistente → **Actualizar menús**. Si el addon no está instalado, su sección se oculta. |
