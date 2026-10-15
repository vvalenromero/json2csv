"""json2csv: conversión de JSON a CSV con arquitectura de filtros.

Expone la versión del paquete y la función de conversión, de modo que el
proyecto pueda usarse tanto como herramienta de línea de comandos como
biblioteca.
"""

from __future__ import annotations

from .pipeline import (
    ErrorDeEntrada,
    ErrorDeRegistro,
    ErrorDeSalida,
    convertir,
    escribir_csv,
    filtrar_campos,
)

__version__ = "1.0.0"

__all__ = [
    "ErrorDeEntrada",
    "ErrorDeRegistro",
    "ErrorDeSalida",
    "__version__",
    "convertir",
    "escribir_csv",
    "filtrar_campos",
]
