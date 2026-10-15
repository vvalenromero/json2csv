# Registro de cambios

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue las convenciones de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto se adhiere a [Versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado

- Estructura inicial del proyecto generada con CookieCutter.
- Conversión de JSON a CSV con arquitectura de filtros independientes.
- Decodificación de documento JSON completo, objeto suelto y JSON Lines.
- Aplanado de objetos anidados con separador configurable.
- Filtro de campos por inclusión y por exclusión.
- Interfaz de línea de comandos con `-i`, `-o`, `-d`, `--incluir`, `--excluir`, `--separador`.
- Entrada y salida estándar cuando no se informan `-i` y `-o`.
- Controles de excepción con códigos de salida diferenciados.
- Suite de pruebas del pipeline y de la interfaz, con cobertura mínima exigida del 85%.
- Integración continua con ruff, black, mypy, pyright, bandit, pytest y pdoc.
- Publicación automática de la documentación de la API en GitHub Pages.
- Registro automático de `VERSION` y `BUILD`.

## [1.0.0] - 2026-10-14

### Agregado

- Primera versión funcional de la herramienta.
