#!/usr/bin/env python3
"""Punto de entrada de la herramienta json2csv.

Es el archivo que el enunciado exige poder ejecutar como::

    python json2csv.py {-i input.txt} {-o output.txt} {-d delimitador}

El programa real vive en el paquete ``src/json2csv``; este archivo agrega el
directorio ``src`` al camino de importación y delega en él. La separación
existe para que la lógica pueda importarse y probarse sin ejecutar un script.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from json2csv_tool.cli import main

if __name__ == "__main__":
    sys.exit(main())
