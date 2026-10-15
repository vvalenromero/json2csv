# Documentación de json2csv

La documentación de referencia de la API se genera automáticamente con `pdoc` a
partir de los docstrings del paquete, y se publica en GitHub Pages en cada
confirmación sobre la rama principal.

Para generarla localmente:

```bash
python -m pdoc --output-dir docs/api src/json2csv_tool
```

## Documentación escrita a mano

- [README](../README.md): qué hace el programa, instalación, uso, formas de entrada admitidas,
  códigos de salida y controles de calidad.
- [CONTEXT](../CONTEXT.md): prompts de las herramientas de inteligencia artificial usadas.
- [CHANGELOG](../CHANGELOG.md): registro de cambios por versión.
