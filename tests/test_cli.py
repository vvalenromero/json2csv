"""Pruebas de la interfaz de línea de comandos.

Se ejercita el programa por su interfaz pública: los argumentos, los flujos
estándar, los archivos y el código de salida. Es la verificación de que las
condiciones de excepción terminen en un mensaje y no en una traza.

Nota sobre la captura de la salida estándar: los casos que necesitan observar
lo escrito en la salida estándar reemplazan ``sys.stdout`` por un búfer propio
en lugar de usar el accesorio ``capsys``. Mezclar ``capsys`` —que cambia el
modo de captura de todo el proceso— con casos que lanzan subprocesos deja
descriptores inválidos en Windows, y el subproceso falla al heredar los flujos.
Mantener un único modo de captura hace que estos casos sean deterministas.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from json2csv_tool import __version__
from json2csv_tool.cli import (
    CODIGO_ERROR_ENTRADA,
    CODIGO_ERROR_SALIDA,
    CODIGO_ERROR_USO,
    CODIGO_OK,
    construir_analizador,
    ejecutar,
    main,
    validar_delimitador,
)

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "json2csv.py"


class TestValidarDelimitador:
    """El delimitador debe ser un único carácter utilizable en CSV."""

    def test_coma_es_valida(self) -> None:
        assert validar_delimitador(",") == ","

    def test_punto_y_coma_es_valido(self) -> None:
        assert validar_delimitador(";") == ";"

    def test_vacio_es_error(self) -> None:
        with pytest.raises(ValueError) as error:
            validar_delimitador("")
        assert "un único carácter" in str(error.value)

    def test_mas_de_un_caracter_es_error(self) -> None:
        with pytest.raises(ValueError) as error:
            validar_delimitador(";;")
        assert "un único carácter" in str(error.value)

    def test_salto_de_linea_es_error(self) -> None:
        with pytest.raises(ValueError) as error:
            validar_delimitador("\n")
        assert "no puede usarse" in str(error.value)

    def test_comilla_es_error(self) -> None:
        with pytest.raises(ValueError) as error:
            validar_delimitador('"')
        assert "no puede usarse" in str(error.value)


class TestArgumentos:
    """El analizador expone la interfaz exigida por el enunciado."""

    def test_acepta_la_interfaz_del_enunciado(self) -> None:
        opciones = construir_analizador().parse_args(["-i", "e.json", "-o", "s.csv", "-d", ";"])
        assert opciones.input == "e.json"
        assert opciones.output == "s.csv"
        assert opciones.delimiter == ";"

    def test_delimitador_por_omision_es_coma(self) -> None:
        assert construir_analizador().parse_args([]).delimiter == ","

    def test_version_termina_el_programa(self) -> None:
        with pytest.raises(SystemExit) as salida:
            construir_analizador().parse_args(["--version"])
        assert salida.value.code == 0

    def test_ayuda_termina_el_programa(self) -> None:
        with pytest.raises(SystemExit) as salida:
            construir_analizador().parse_args(["-h"])
        assert salida.value.code == 0


class TestEjecutarConArchivos:
    """Conversión usando archivos de entrada y salida reales."""

    def test_conversion_completa(self, tmp_path: Path) -> None:
        entrada = tmp_path / "entrada.json"
        salida = tmp_path / "salida.csv"
        entrada.write_text('[{"a": 1, "b": 2}]', encoding="utf-8")

        codigo = ejecutar(["-i", str(entrada), "-o", str(salida)])

        assert codigo == CODIGO_OK
        assert salida.read_text(encoding="utf-8") == "a,b\n1,2\n"

    def test_delimitador_personalizado(self, tmp_path: Path) -> None:
        entrada = tmp_path / "entrada.json"
        salida = tmp_path / "salida.csv"
        entrada.write_text('[{"a": 1, "b": 2}]', encoding="utf-8")

        ejecutar(["-i", str(entrada), "-o", str(salida), "-d", ";"])

        assert salida.read_text(encoding="utf-8") == "a;b\n1;2\n"

    def test_archivo_inexistente_da_error_de_entrada(self, tmp_path: Path) -> None:
        codigo = ejecutar(["-i", str(tmp_path / "no-existe.json"), "-o", str(tmp_path / "s.csv")])
        assert codigo == CODIGO_ERROR_ENTRADA

    def test_directorio_como_entrada_da_error(self, tmp_path: Path) -> None:
        codigo = ejecutar(["-i", str(tmp_path), "-o", str(tmp_path / "s.csv")])
        assert codigo == CODIGO_ERROR_ENTRADA

    def test_json_invalido_da_error_de_entrada(self, tmp_path: Path) -> None:
        entrada = tmp_path / "roto.json"
        entrada.write_text('{"a": }', encoding="utf-8")
        codigo = ejecutar(["-i", str(entrada), "-o", str(tmp_path / "s.csv")])
        assert codigo == CODIGO_ERROR_ENTRADA

    def test_directorio_de_salida_inexistente_da_error(self, tmp_path: Path) -> None:
        entrada = tmp_path / "e.json"
        entrada.write_text('[{"a": 1}]', encoding="utf-8")
        codigo = ejecutar(["-i", str(entrada), "-o", str(tmp_path / "carpeta" / "s.csv")])
        assert codigo == CODIGO_ERROR_SALIDA

    def test_archivo_con_bom_se_lee(self, tmp_path: Path) -> None:
        entrada = tmp_path / "bom.json"
        entrada.write_bytes('\ufeff[{"a": 1}]'.encode())
        salida = tmp_path / "s.csv"

        assert ejecutar(["-i", str(entrada), "-o", str(salida)]) == CODIGO_OK
        assert salida.read_text(encoding="utf-8") == "a\n1\n"

    def test_archivo_no_utf8_da_error_de_entrada(self, tmp_path: Path) -> None:
        entrada = tmp_path / "latin.json"
        entrada.write_bytes(b'[{"a": "\xf1"}]')
        codigo = ejecutar(["-i", str(entrada), "-o", str(tmp_path / "s.csv")])
        assert codigo == CODIGO_ERROR_ENTRADA


class TestEjecutarConFlujos:
    """Conversión leyendo de la entrada estándar y escribiendo en la salida."""

    def test_entrada_y_salida_estandar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        salida = io.StringIO()
        monkeypatch.setattr(sys, "stdin", io.StringIO('[{"a": 1}]'))
        monkeypatch.setattr(sys, "stdout", salida)

        codigo = ejecutar([])

        assert codigo == CODIGO_OK
        assert salida.getvalue() == "a\n1\n"

    def test_solo_entrada_estandar_con_archivo_de_salida(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO('[{"a": 1}]'))
        salida = tmp_path / "s.csv"

        assert ejecutar(["-o", str(salida)]) == CODIGO_OK
        assert salida.read_text(encoding="utf-8") == "a\n1\n"

    def test_entrada_vacia_da_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        monkeypatch.setattr(sys, "stdout", io.StringIO())

        assert ejecutar([]) == CODIGO_ERROR_ENTRADA


class TestErroresDeUso:
    """Los argumentos incompatibles se informan sin ejecutar la conversión."""

    def test_incluir_y_excluir_juntos_dan_error_de_uso(self) -> None:
        codigo = ejecutar(["--incluir", "a", "--excluir", "b"])
        assert codigo == CODIGO_ERROR_USO

    def test_delimitador_invalido_da_error_de_uso(self, tmp_path: Path) -> None:
        entrada = tmp_path / "e.json"
        entrada.write_text('[{"a": 1}]', encoding="utf-8")
        codigo = ejecutar(["-i", str(entrada), "-d", "xx"])
        assert codigo == CODIGO_ERROR_USO


class TestMain:
    """El punto de entrada devuelve el código de salida del proceso."""

    def test_main_conversion_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO('[{"a": 1}]'))
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        assert main([]) == CODIGO_OK

    def test_version_se_informa(self) -> None:
        assert __version__


class TestEjecucionComoModulo:
    """El paquete también se ejecuta con ``python -m json2csv``."""

    def test_modulo_convierte_desde_la_entrada_estandar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import runpy

        salida_estandar = io.StringIO()
        monkeypatch.setattr(sys, "stdin", io.StringIO('[{"a": 1}]'))
        monkeypatch.setattr(sys, "stdout", salida_estandar)
        monkeypatch.setattr(sys, "argv", ["json2csv"])

        with pytest.raises(SystemExit) as salida:
            runpy.run_module("json2csv_tool", run_name="__main__")

        assert salida.value.code == CODIGO_OK
        assert salida_estandar.getvalue() == "a\n1\n"

    def test_modulo_informa_la_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import runpy

        monkeypatch.setattr(sys, "argv", ["json2csv", "--version"])

        with pytest.raises(SystemExit) as salida:
            runpy.run_module("json2csv_tool", run_name="__main__")

        assert salida.value.code == CODIGO_OK


class TestExtremoAExtremo:
    """Se ejecuta el script tal como lo invoca el enunciado."""

    def test_script_con_archivos(self, tmp_path: Path) -> None:
        entrada = tmp_path / "entrada.json"
        salida = tmp_path / "salida.csv"
        entrada.write_text('[{"nombre": "Ana", "edad": 30}]', encoding="utf-8")

        proceso = subprocess.run(
            [sys.executable, str(SCRIPT), "-i", str(entrada), "-o", str(salida)],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.returncode == CODIGO_OK
        assert salida.read_text(encoding="utf-8") == "nombre,edad\nAna,30\n"

    def test_script_por_entrada_estandar(self) -> None:
        proceso = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input='[{"a": 1}]',
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.returncode == CODIGO_OK
        assert proceso.stdout == "a\n1\n"

    def test_script_no_imprime_traza_ante_json_invalido(self) -> None:
        proceso = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="{roto}",
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.returncode == CODIGO_ERROR_ENTRADA
        assert "Traceback" not in proceso.stderr
        assert "error" in proceso.stderr

    def test_script_informa_la_version(self) -> None:
        proceso = subprocess.run(
            [sys.executable, str(SCRIPT), "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.returncode == 0
        assert __version__ in proceso.stdout

    def test_script_con_delimitador(self) -> None:
        proceso = subprocess.run(
            [sys.executable, str(SCRIPT), "-d", "|"],
            input='[{"a": 1, "b": 2}]',
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.stdout == "a|b\n1|2\n"

    def test_script_filtra_por_inclusion(self) -> None:
        proceso = subprocess.run(
            [sys.executable, str(SCRIPT), "--incluir", "b"],
            input='[{"a": 1, "b": 2}]',
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        assert proceso.stdout == "b\n2\n"
