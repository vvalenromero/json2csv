"""Interfaz de línea de comandos de la herramienta json2csv.

Traduce los argumentos en un pipeline y concentra el manejo de las condiciones
de excepción: ninguna entrada incorrecta del usuario debe terminar en una traza
de Python. Cada familia de error tiene su propio código de salida, para que el
programa pueda usarse desde un script o desde la integración continua.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from . import __version__
from .pipeline import (
    SEPARADOR_ANIDADO,
    ErrorDeEntrada,
    ErrorDeRegistro,
    ErrorDeSalida,
    convertir,
    informar_error,
)

CODIGO_OK = 0
CODIGO_ERROR_ENTRADA = 1
CODIGO_ERROR_USO = 2
CODIGO_ERROR_SALIDA = 3

DELIMITADOR_POR_DEFECTO = ","


def construir_analizador() -> argparse.ArgumentParser:
    """Arma el analizador de argumentos de línea de comandos.

    Returns:
        El analizador configurado con la interfaz pedida por el enunciado más
        las opciones de filtrado de campos.
    """
    analizador = argparse.ArgumentParser(
        prog="json2csv",
        description="Convierte un documento JSON a formato CSV usando un pipeline de filtros.",
        epilog=(
            "Si no se indica -i la entrada se lee de la entrada estándar; "
            "si no se indica -o el resultado se escribe en la salida estándar. "
            "Se admiten un documento JSON completo y JSON Lines."
        ),
    )
    analizador.add_argument("-i", "--input", metavar="ARCHIVO", help="archivo JSON de entrada.")
    analizador.add_argument("-o", "--output", metavar="ARCHIVO", help="archivo CSV de salida.")
    analizador.add_argument(
        "-d",
        "--delimiter",
        metavar="DELIMITADOR",
        default=DELIMITADOR_POR_DEFECTO,
        help="delimitador de columnas (por omisión la coma).",
    )
    analizador.add_argument(
        "--incluir",
        nargs="+",
        metavar="CAMPO",
        default=[],
        help="emite únicamente estos campos, en el orden indicado.",
    )
    analizador.add_argument(
        "--excluir",
        nargs="+",
        metavar="CAMPO",
        default=[],
        help="emite todos los campos menos estos.",
    )
    analizador.add_argument(
        "--separador",
        metavar="TEXTO",
        default=SEPARADOR_ANIDADO,
        help="texto que une los nombres de los objetos anidados (por omisión el punto).",
    )
    analizador.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"json2csv {__version__}",
    )
    return analizador


@contextmanager
def _entrada(ruta: str | None) -> Iterator[TextIO]:
    """Abre la entrada indicada o deja disponible la entrada estándar.

    Args:
        ruta: ruta del archivo de entrada, o ``None`` para la entrada estándar.

    Yields:
        El flujo de texto del que leer.

    Raises:
        ErrorDeEntrada: si el archivo no existe, no es legible o no está
            codificado en UTF-8.
    """
    if ruta is None:
        yield sys.stdin
        return
    try:
        with Path(ruta).open(encoding="utf-8-sig") as flujo:
            yield flujo
    except FileNotFoundError as error:
        raise ErrorDeEntrada(f"no existe el archivo de entrada '{ruta}'.") from error
    except IsADirectoryError as error:
        raise ErrorDeEntrada(f"'{ruta}' es un directorio, no un archivo.") from error
    except PermissionError as error:
        raise ErrorDeEntrada(f"no hay permiso para leer '{ruta}'.") from error
    except UnicodeDecodeError as error:
        raise ErrorDeEntrada(
            f"el archivo '{ruta}' no está codificado en UTF-8 ({error.reason})."
        ) from error


@contextmanager
def _salida(ruta: str | None) -> Iterator[TextIO]:
    """Abre la salida indicada o deja disponible la salida estándar.

    Args:
        ruta: ruta del archivo de salida, o ``None`` para la salida estándar.

    Yields:
        El flujo de texto donde escribir.

    Raises:
        ErrorDeSalida: si no se puede crear o escribir el archivo indicado.
    """
    if ruta is None:
        yield sys.stdout
        return
    try:
        destino = Path(ruta)
        if destino.parent and not destino.parent.exists():
            raise ErrorDeSalida(f"no existe el directorio '{destino.parent}'.")
        with destino.open("w", encoding="utf-8", newline="") as flujo:
            yield flujo
    except PermissionError as error:
        raise ErrorDeSalida(f"no hay permiso para escribir '{ruta}'.") from error
    except IsADirectoryError as error:
        raise ErrorDeSalida(f"'{ruta}' es un directorio, no un archivo.") from error


def validar_delimitador(delimitador: str) -> str:
    """Comprueba que el delimitador sea un único carácter.

    Args:
        delimitador: valor recibido por la opción ``-d``.

    Returns:
        El delimitador validado.

    Raises:
        ValueError: si el delimitador no tiene exactamente un carácter.
    """
    if len(delimitador) != 1:
        raise ValueError(f"el delimitador debe ser un único carácter y se recibió '{delimitador}'.")
    if delimitador in {"\n", "\r", '"'}:
        raise ValueError(f"el delimitador '{delimitador}' no puede usarse en CSV.")
    return delimitador


def ejecutar(argumentos: Sequence[str] | None = None) -> int:
    """Ejecuta la herramienta y devuelve el código de salida.

    Args:
        argumentos: argumentos de línea de comandos; por omisión los del proceso.

    Returns:
        ``0`` si la conversión terminó bien; ``1`` ante un problema de entrada,
        ``2`` ante un uso incorrecto y ``3`` ante un problema de salida.
    """
    analizador = construir_analizador()
    opciones = analizador.parse_args(argumentos)

    if opciones.incluir and opciones.excluir:
        informar_error("no se pueden indicar a la vez --incluir y --excluir.")
        return CODIGO_ERROR_USO

    try:
        delimitador = validar_delimitador(opciones.delimiter)
    except ValueError as error:
        informar_error(str(error))
        return CODIGO_ERROR_USO

    try:
        with _entrada(opciones.input) as origen:
            texto = origen.read()
        with _salida(opciones.output) as destino:
            filas = convertir(
                texto,
                destino,
                delimitador=delimitador,
                incluir=opciones.incluir,
                excluir=opciones.excluir,
                origen=opciones.input or "<entrada estándar>",
                separador=opciones.separador,
            )
    except (ErrorDeEntrada, ErrorDeRegistro) as error:
        informar_error(str(error))
        return CODIGO_ERROR_ENTRADA
    except ErrorDeSalida as error:
        informar_error(str(error))
        return CODIGO_ERROR_SALIDA
    except BrokenPipeError:
        # Ocurre cuando el consumidor del pipe cierra antes de tiempo, por
        # ejemplo al usar `json2csv ... | head`. No es un error del programa.
        return CODIGO_OK
    except KeyboardInterrupt:
        informar_error("interrumpido por el usuario.")
        return 130

    if opciones.output:
        print(f"json2csv: {filas} filas escritas en '{opciones.output}'.", file=sys.stderr)
    return CODIGO_OK


def main(argumentos: Sequence[str] | None = None) -> int:
    """Punto de entrada del programa.

    Args:
        argumentos: argumentos de línea de comandos; por omisión los del proceso.

    Returns:
        El código de salida del proceso.
    """
    _configurar_utf8()
    return ejecutar(argumentos)


def _configurar_utf8() -> None:
    """Fuerza UTF-8 en los flujos estándar que todavía no lo usen.

    En Windows la salida estándar usa por omisión la página de códigos del
    sistema, que no puede representar los acentos ni las comillas tipográficas
    que suelen traer los datos JSON.

    Solo se reconfigura el flujo cuando su codificación **no es ya** UTF-8. La
    comprobación previa no es una optimización: reconfigurar un flujo que ya
    está correcto reemplaza el búfer interno y deja inválidos los descriptores
    que el proceso anfitrión —por ejemplo un marco de pruebas o un lanzador de
    subprocesos— pudiera estar usando sobre ese mismo flujo.
    """
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        codificacion = (getattr(flujo, "encoding", "") or "").lower().replace("-", "")
        if codificacion.startswith("utf8"):
            continue
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is None:
            continue
        try:
            reconfigurar(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            # Un flujo que no admite reconfiguración no debe impedir la
            # ejecución: se continúa con la codificación que ya tenga.
            continue
