# json2csv

[![CI](https://github.com/vvalenromero/json2csv/actions/workflows/ci.yml/badge.svg)](https://github.com/vvalenromero/json2csv/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Herramienta de linea de comandos para convertir JSON a CSV con arquitectura de filtros.

## Qué hace

Convierte un documento JSON en un archivo CSV. El programa no implementa la conversión como un
procedimiento monolítico sino como un **pipeline de filtros independientes**: cada etapa recibe
un iterable de registros y devuelve otro, y el resultado se compone encadenándolas.

```
origen → leer_texto → decodificar → como_registros → aplanar
       → filtrar_campos → escribir_csv → destino
```

Cada filtro se prueba por separado y se puede reemplazar sin tocar los demás.

## Instalación

El proyecto se desarrolla dentro de un ambiente virtual de Python (`venv`), como exige el
enunciado.

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
```

## Uso

La interfaz es la que fija el enunciado:

```
python json2csv.py {-i input.txt} {-o output.txt} {-d delimitador}
```

- Si no se informa `-i`, la entrada se lee de la **entrada estándar**.
- Si no se informa `-o`, el resultado se escribe en la **salida estándar**.
- El delimitador por omisión es la **coma**; se cambia con `-d`.

```bash
# archivo a archivo
python json2csv.py -i personas.json -o personas.csv

# por tubería, con punto y coma como delimitador
cat personas.json | python json2csv.py -d ';' > personas.csv

# solo algunos campos
python json2csv.py -i personas.json --incluir nombre edad

# todos menos algunos
python json2csv.py -i personas.json --excluir interno
```

### Formas de entrada admitidas

| Forma | Ejemplo |
|-------|---------|
| Documento JSON con lista de objetos | `[{"a": 1}, {"a": 2}]` |
| Documento JSON con un objeto suelto | `{"a": 1}` |
| JSON Lines, un objeto por línea | `{"a": 1}`<br>`{"a": 2}` |
| Lista de listas | `[["x", "y"], ["z", "w"]]` |

### Cómo se resuelven los datos anidados

Los objetos anidados se aplanan uniendo los nombres con un punto, y las listas se serializan
como JSON dentro de la celda, porque no tienen una representación unívoca en CSV.

```json
{"persona": {"nombre": "Ana"}, "hobbies": ["leer", "correr"]}
```

```csv
persona.nombre,hobbies
Ana,"[""leer"", ""correr""]"
```

El separador de anidación se cambia con `--separador`.

### Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | La conversión terminó bien. |
| 1 | Problema en la entrada: archivo inexistente, JSON inválido, codificación incorrecta. |
| 2 | Uso incorrecto: argumentos incompatibles o delimitador inválido. |
| 3 | Problema en la salida: no se pudo crear o escribir el archivo. |

Ninguna entrada incorrecta termina en una traza de Python: siempre hay un mensaje en la salida
de errores.

## Calidad

El proyecto mantiene estos controles, todos automatizados en la integración continua:

| Control | Herramienta | Exigencia |
|---------|-------------|-----------|
| Reglas de estilo y errores | `ruff` | sin observaciones |
| Formato consistente | `black` | sin diferencias |
| Convenciones de estilo | PEP8 (vía ruff) | sin observaciones |
| Docstrings | PEP257 (vía ruff) | sin observaciones |
| Tipado estático | `mypy` en modo estricto | sin errores |
| Tipado estático | `pyright` | sin errores |
| Pruebas unitarias | `pytest` | todo en verde |
| Cobertura | `pytest-cov` | 85% o mejor |
| Seguridad | `bandit` | sin observaciones |
| Documentación | `pdoc` | se genera y se publica |

```bash
python -m ruff check . && python -m ruff format --check .
python -m black --check .
python -m mypy src tests json2csv.py
python -m pyright
python -m bandit -r src -c pyproject.toml
python -m pytest
python -m pdoc --output-dir docs/api src/json2csv_tool
```

Deliberadamente **no se usa Trufflehog** entre los controles de seguridad, según lo indicado en
el enunciado; el análisis de seguridad se cubre con `bandit`.

## Estructura

```
.
├── .github/workflows/ci.yml   Integración continua completa
├── BUILD                      Número de compilación, lo incrementa la CI
├── CHANGELOG.md               Registro de cambios
├── CONTEXT.md                 Prompts de las herramientas de IA usadas
├── LICENSE                    Licencia MIT
├── README.md                  Este archivo
├── VERSION                    Versión del proyecto
├── json2csv.py                Punto de entrada ejecutable (el que pide el enunciado)
├── pyproject.toml             Configuración del paquete y de todas las herramientas
├── requirements.txt           Dependencias de ejecución
├── requirements-dev.txt       Dependencias de desarrollo
├── docs/                      Documentación de la API generada por pdoc
├── src/json2csv_tool/              Paquete: pipeline.py y cli.py
└── tests/                     Pruebas del pipeline y de la interfaz
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
