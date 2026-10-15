"""Permite ejecutar el paquete como módulo con ``python -m json2csv``."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
