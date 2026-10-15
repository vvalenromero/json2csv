# CONTEXT — Prompts de las herramientas de inteligencia artificial

Según lo exige el enunciado (`c.`), en este archivo se documentan los prompts utilizados con
herramientas de IA durante el desarrollo del proyecto, y qué se obtuvo de cada uno.

## Herramienta utilizada

**Pi** (`@earendil-works/pi-coding-agent`), agente de programación en terminal, con el arnés
*Gentle AI / el Gentleman* y el flujo de trabajo Organic Driven Development. Modelo de lenguaje
utilizado como asistente de desarrollo, siempre bajo dirección humana: el agente propone y
ejecuta, la persona decide.

## Prompts

### P1 — Enunciado del trabajo práctico

> Desarrollar una herramienta en lenguaje Python para convertir archivos de formato JSON a
> formato CSV. El programa deberá implementarse con una estrategia de filtro. El formato de
> ejecución será: `python json2csv.py {-i input.txt} {-o output.txt} {-d delimitador}`. Si no se
> informa `-i` el programa podrá aceptar el archivo de entrada mediante entrada estándar, al
> mismo tiempo si no se informa `-o` se emitirá el texto resultante mediante salida estándar. Se
> utilizará la coma como delimitador, excepto que se indique uno distinto con `-d`. Asegurar la
> implementación de controles robustos para las condiciones de excepción. Implementar el proyecto
> en GitHub con integración continua completa.

**Resultado:** la totalidad del proyecto —este mismo repositorio—.

### P2 — Interpretación de la "estrategia de filtro"

> Explícame qué significa "estrategia de filtro" en el contexto de un conversor JSON a CSV y
> cuál es la diferencia entre la arquitectura de pipe and filter y un filtrado de campos.

**Resultado:** la decisión de implementar las dos lecturas a la vez. La conversión se arma como
un pipeline de generadores encadenados (`pipeline.py`) y además el pipeline expone un filtro de
campos explícito (`filtrar_campos`), con las opciones `--incluir` y `--excluir` en la interfaz.

### P3 — Esqueleto del proyecto con CookieCutter

> Necesito un esqueleto de proyecto Python basado en CookieCutter, con ambiente virtual,
> `pyproject.toml`, licencia MIT, `README.md`, `CHANGELOG.md`, `VERSION`, `BUILD`,
> `requirements.txt` y pruebas con cobertura mínima del 85%.

**Resultado:** la plantilla `cookiecutter-json2csv/`, con la que se generó este repositorio. La
plantilla queda versionada junto al proyecto para que la generación sea reproducible.

### P4 — Condiciones de excepción

> Listame todas las condiciones de excepción que puede encontrar un conversor JSON a CSV que lee
> de archivo o de la entrada estándar y escribe en archivo o en la salida estándar, y cómo debería
> comportarse cada una.

**Resultado:** la tabla de códigos de salida y el conjunto de controles de `cli.py`: archivo
inexistente, directorio en lugar de archivo, falta de permisos, codificación distinta de UTF-8,
BOM, JSON inválido con línea y columna, lista vacía, delimitador inválido, directorio de salida
inexistente, tubería cerrada por el consumidor e interrupción por teclado.

### P5 — Revisión de la calidad

> Revisá el código y decime qué observarían ruff, black, mypy en modo estricto y bandit.

**Resultado:** los ajustes de anotaciones de tipo, el uso de `pathlib`, la conversión de literales
obsoletos y la reescritura de los bloques de excepción con `raise ... from error`.

## Criterio de uso

Las herramientas de IA se usaron como asistente de programación bajo dirección humana:

- Cada decisión de diseño fue revisada y aprobada antes de escribir código.
- El enunciado se trató como especificación cerrada; el agente no agregó requisitos.
- La corrección de cada control de calidad se verificó ejecutando la herramienta, no por
  afirmación del agente: los resultados de `ruff`, `black`, `mypy`, `pyright`, `bandit` y
  `pytest` quedan registrados en la integración continua.
