"""Filtros del pipeline de conversión de JSON a CSV.

La conversión no se implementa como un procedimiento monolítico sino como un
**pipeline de filtros independientes**: cada etapa recibe un iterable de
registros y devuelve otro iterable, y el resultado final se obtiene encadenando
las etapas.

La consecuencia práctica es que cada filtro se prueba por separado, se reordena
o se reemplaza sin tocar los demás, y el costo de comprender una etapa no crece
con el tamaño del pipeline. Las etapas se comunican únicamente por el valor que
transportan, nunca por estado compartido.

Pipeline por defecto::

    origen -> leer_texto -> decodificar -> como_registros -> aplanar
           -> filtrar_campos -> escribir_csv -> destino
"""

from __future__ import annotations

import csv
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import IO, Any

SEPARADOR_ANIDADO = "."


class ErrorDeEntrada(ValueError):
    """La entrada no puede interpretarse como un documento JSON válido."""


class ErrorDeRegistro(ValueError):
    """Un elemento de la entrada no tiene una forma convertible a fila."""


class ErrorDeSalida(OSError):
    """No se pudo escribir el resultado en el destino indicado."""


# --- Etapa 1: decodificación ---------------------------------------------


def decodificar(texto: str, origen: str = "<entrada>") -> Any:
    """Convierte el texto de entrada en la estructura de datos de JSON.

    Acepta las dos formas habituales de documento:

    * un **documento JSON completo**: una lista de registros o un único objeto;
    * **JSON Lines**: un objeto por línea, sin comas ni corchetes envolventes.

    Args:
        texto: contenido crudo de la entrada.
        origen: nombre de la entrada, que se usa en los mensajes de error.

    Returns:
        La estructura decodificada.

    Raises:
        ErrorDeEntrada: si el texto está vacío, no es JSON válido en ninguna de
            las dos formas admitidas, o la lista de registros está vacía.
    """
    if not texto.strip():
        raise ErrorDeEntrada(f"{origen}: la entrada está vacía.")

    error_documento: json.JSONDecodeError | None = None
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        error_documento = error
    else:
        if isinstance(datos, list) and not datos:
            raise ErrorDeEntrada(f"{origen}: la lista de registros está vacía.")
        return datos

    datos_lineas = _decodificar_lineas(texto, origen)
    if datos_lineas is not None:
        return datos_lineas

    raise ErrorDeEntrada(
        f"{origen}: JSON inválido en la línea {error_documento.lineno}, "
        f"columna {error_documento.colno}: {error_documento.msg}."
    )


def _decodificar_lineas(texto: str, origen: str) -> list[Any] | None:
    """Intenta interpretar la entrada como JSON Lines.

    Args:
        texto: contenido crudo de la entrada.
        origen: nombre de la entrada para los mensajes de error.

    Returns:
        La lista de objetos si todas las líneas no vacías son JSON válido, o
        ``None`` si la entrada no tiene forma de JSON Lines.
    """
    registros: list[Any] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            if not registros:
                return None
            raise ErrorDeEntrada(
                f"{origen}: la línea {numero} no es un objeto JSON válido."
            ) from None
    return registros or None


# --- Etapa 2: normalización a registros ----------------------------------


def como_registros(datos: Any) -> Iterator[Mapping[str, Any]]:
    """Normaliza la estructura decodificada a una secuencia de registros.

    Admite un objeto suelto (se emite como un único registro), una lista de
    objetos, y una lista de listas (en cuyo caso las columnas se numeran).

    Args:
        datos: estructura devuelta por :func:`decodificar`.

    Yields:
        Un mapeo de nombre de campo a valor por cada registro.

    Raises:
        ErrorDeRegistro: si un elemento no es un objeto, una lista de valores
            planos, ni un escalar suelto.
    """
    if isinstance(datos, Mapping):
        yield datos
        return
    if not isinstance(datos, Sequence):
        yield {"valor": datos}
        return

    for elemento in datos:
        if isinstance(elemento, Mapping):
            yield elemento
        elif isinstance(elemento, Sequence) and not isinstance(elemento, (str, bytes)):
            yield {str(indice): valor for indice, valor in enumerate(elemento)}
        else:
            yield {"valor": elemento}


# --- Etapa 3: aplanado ---------------------------------------------------


def aplanar_valor(valor: Any, prefijo: str, separador: str = SEPARADOR_ANIDADO) -> dict[str, Any]:
    """Aplana recursivamente un valor en un diccionario de un solo nivel.

    Los objetos anidados se expanden uniendo los nombres con el separador; las
    listas y los objetos dentro de listas se conservan serializados como JSON,
    porque no tienen una representación unívoca en una celda de CSV.

    Args:
        valor: valor a aplanar.
        prefijo: nombre de campo acumulado hasta este nivel.
        separador: texto que une los nombres de los niveles anidados.

    Returns:
        Un diccionario con un campo por hoja del valor recibido.
    """
    if isinstance(valor, Mapping):
        aplanado: dict[str, Any] = {}
        for clave, anidado in valor.items():
            nombre = f"{prefijo}{separador}{clave}" if prefijo else str(clave)
            aplanado.update(aplanar_valor(anidado, nombre, separador))
        if aplanado:
            return aplanado
        # Un objeto vacío conserva su columna con la celda vacía, salvo en la
        # raíz, donde no hay ningún nombre de columna que conservar.
        return {prefijo: ""} if prefijo else {}
    if isinstance(valor, (list, tuple, set)):
        return {prefijo: json.dumps(list(valor), ensure_ascii=False, default=str)}
    return {prefijo: valor}


def aplanar(
    registros: Iterable[Mapping[str, Any]],
    separador: str = SEPARADOR_ANIDADO,
) -> Iterator[dict[str, Any]]:
    """Aplana cada registro a un diccionario de un solo nivel.

    Args:
        registros: iterable de registros posiblemente anidados.
        separador: texto que une los nombres de los niveles anidados.

    Yields:
        Un registro plano por cada registro de entrada.
    """
    for registro in registros:
        plano: dict[str, Any] = {}
        for clave, valor in registro.items():
            plano.update(aplanar_valor(valor, str(clave), separador))
        yield plano


# --- Etapa 4: filtro de campos -------------------------------------------


def filtrar_campos(
    registros: Iterable[Mapping[str, Any]],
    incluir: Sequence[str] = (),
    excluir: Sequence[str] = (),
) -> Iterator[dict[str, Any]]:
    """Selecciona qué campos de cada registro llegan a la salida.

    Es el filtro propiamente dicho del pipeline: decide qué información pasa.
    Si se indica ``incluir``, solo se emiten esos campos, en ese orden. Si se
    indica ``excluir``, se emiten todos menos esos. Los campos ausentes en un
    registro quedan como cadena vacía, para que la fila conserve las columnas.

    Args:
        registros: iterable de registros planos.
        incluir: nombres de campo a conservar, en el orden de salida deseado.
        excluir: nombres de campo a descartar.

    Yields:
        El registro reducido a los campos seleccionados.

    Raises:
        ValueError: si se informan ``incluir`` y ``excluir`` a la vez, porque
            la selección sería ambigua.
    """
    if incluir and excluir:
        raise ValueError("no se pueden indicar a la vez los campos a incluir y a excluir.")

    descartados = set(excluir)
    for registro in registros:
        if incluir:
            yield {campo: registro.get(campo, "") for campo in incluir}
        else:
            yield {campo: valor for campo, valor in registro.items() if campo not in descartados}


# --- Etapa 5: salida -----------------------------------------------------


def calcular_encabezado(registros: Sequence[Mapping[str, Any]]) -> list[str]:
    """Calcula la lista de columnas como unión de los campos de los registros.

    Mantiene el orden de primera aparición, de modo que la salida es estable
    entre corridas para la misma entrada.

    Args:
        registros: registros planos ya filtrados.

    Returns:
        Los nombres de columna, sin repetir.
    """
    columnas: dict[str, None] = {}
    for registro in registros:
        for campo in registro:
            columnas.setdefault(campo, None)
    return list(columnas)


def _celda(valor: Any) -> str:
    """Convierte un valor JSON en el texto de una celda de CSV.

    Args:
        valor: valor del registro.

    Returns:
        La representación textual: cadena vacía para ``None``, el JSON de las
        estructuras y la forma habitual de los escalares.
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str)
    return str(valor)


def escribir_csv(
    registros: Sequence[Mapping[str, Any]],
    destino: IO[str],
    delimitador: str,
) -> int:
    """Escribe los registros en formato CSV y devuelve la cantidad de filas.

    Args:
        registros: registros planos ya filtrados.
        destino: flujo de texto donde se escribe el CSV.
        delimitador: carácter separador de columnas.

    Returns:
        La cantidad de filas de datos escritas, sin contar el encabezado.

    Raises:
        ErrorDeSalida: si falla la escritura en el destino.
    """
    encabezado = calcular_encabezado(registros)
    try:
        escritor = csv.DictWriter(
            destino,
            fieldnames=encabezado,
            delimiter=delimitador,
            extrasaction="ignore",
            lineterminator="\n",
        )
        if encabezado:
            escritor.writeheader()
        filas = 0
        for registro in registros:
            escritor.writerow({campo: _celda(valor) for campo, valor in registro.items()})
            filas += 1
        destino.flush()
    except OSError as error:
        raise ErrorDeSalida(f"no se pudo escribir la salida: {error}") from error
    return filas


# --- Armado del pipeline -------------------------------------------------


def convertir(
    texto: str,
    destino: IO[str],
    delimitador: str = ",",
    incluir: Sequence[str] = (),
    excluir: Sequence[str] = (),
    origen: str = "<entrada>",
    separador: str = SEPARADOR_ANIDADO,
) -> int:
    """Encadena los filtros y ejecuta la conversión completa.

    Es el único punto donde las etapas se conocen entre sí: cada una sigue
    siendo independiente y reemplazable.

    Args:
        texto: contenido crudo de la entrada.
        destino: flujo de texto donde se escribe el CSV.
        delimitador: carácter separador de columnas.
        incluir: nombres de campo a conservar.
        excluir: nombres de campo a descartar.
        origen: nombre de la entrada para los mensajes de error.
        separador: texto que une los nombres de los niveles anidados.

    Returns:
        La cantidad de filas de datos escritas.
    """
    datos = decodificar(texto, origen)
    planos = aplanar(como_registros(datos), separador)
    seleccionados = filtrar_campos(planos, incluir, excluir)
    return escribir_csv(list(seleccionados), destino, delimitador)


def informar_error(mensaje: str) -> None:
    """Escribe un mensaje de error en la salida estándar de errores.

    Args:
        mensaje: texto a informar.
    """
    print(f"json2csv: error: {mensaje}", file=sys.stderr)
