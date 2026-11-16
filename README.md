# Kodi de Papá

Repositorio Kodi (GitHub Pages en `docs/`) con el asistente `script.papa.inicio`, que monta en Kodi 21 Omega un menú estilo Apple TV (Arctic Fuse 3) con Palantir y BlackGhost.

- Guía de instalación: [GUIA.md](GUIA.md)
- Diseño: `docs/superpowers/specs/2026-11-16-kodi-papa-design.md`

## Desarrollo

```bash
pip install pytest Kodistubs==21.0.0
python3 -m pytest tests -q          # pruebas
python3 tools/make_icons.py         # iconos
python3 tools/build_repo.py         # regenera docs/ (zips, addons.xml, md5)
```

Para publicar una actualización, sube el `version` en `src/<addon>/addon.xml`, ejecuta `tools/build_repo.py` y fusiona en `main`. La caja la instala sola.
