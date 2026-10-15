"""Pruebas de los filtros del pipeline, ejercitados de a uno.

Cada filtro se prueba por separado, que es la ventaja de construirlos como
funciones independientes sobre iterables.
"""

from __future__ import annotations

import io
import json

import pytest

from json2csv_tool.pipeline import (
    ErrorDeEntrada,
    aplanar,
    aplanar_valor,
    calcular_encabezado,
    como_registros,
    convertir,
    decodificar,
    escribir_csv,
    filtrar_campos,
)


class TestDecodificar:
    """El filtro de decodificación acepta las formas de documento admitidas."""

    def test_documento_json_de_lista(self) -> None:
        datos = decodificar('[{"a": 1}]')
        assert datos == [{"a": 1}]

    def test_documento_json_de_objeto(self) -> None:
        datos = decodificar('{"a": 1}')
        assert datos == {"a": 1}

    def test_json_lines(self) -> None:
        datos = decodificar('{"a": 1}\n{"a": 2}\n')
        assert datos == [{"a": 1}, {"a": 2}]

    def test_json_lines_con_lineas_vacias(self) -> None:
        datos = decodificar('\n{"a": 1}\n\n{"a": 2}\n\n')
        assert datos == [{"a": 1}, {"a": 2}]

    def test_lista_vacia_es_error_de_entrada(self) -> None:
        with pytest.raises(ErrorDeEntrada) as error:
            decodificar("[]")
        assert "lista de registros está vacía" in str(error.value)

    def test_entrada_vacia_es_error_de_entrada(self) -> None:
        with pytest.raises(ErrorDeEntrada) as error:
            decodificar("   \n  ")
        assert "está vacía" in str(error.value)

    def test_json_invalido_informa_linea_y_columna(self) -> None:
        with pytest.raises(ErrorDeEntrada) as error:
            decodificar('[{"a": 1},\n{"a": }]')
        assert "línea 2, columna" in str(error.value)

    def test_origen_aparece_en_el_mensaje(self) -> None:
        with pytest.raises(ErrorDeEntrada) as error:
            decodificar("{", origen="datos.json")
        assert "datos.json" in str(error.value)

    def test_json_lines_con_linea_invalida_detecta_el_numero(self) -> None:
        with pytest.raises(ErrorDeEntrada) as error:
            decodificar('{"a": 1}\n{roto}\n')
        assert "línea 2" in str(error.value)


class TestComoRegistros:
    """El filtro de normalización produce un mapeo por registro."""

    def test_lista_de_objetos(self) -> None:
        assert list(como_registros([{"a": 1}, {"a": 2}])) == [{"a": 1}, {"a": 2}]

    def test_objeto_suelto_se_emite_como_un_registro(self) -> None:
        assert list(como_registros({"a": 1})) == [{"a": 1}]

    def test_lista_de_listas_numera_las_columnas(self) -> None:
        assert list(como_registros([["x", "y"]])) == [{"0": "x", "1": "y"}]

    def test_escalar_suelto_va_al_campo_valor(self) -> None:
        assert list(como_registros(7)) == [{"valor": 7}]

    def test_lista_de_escalares(self) -> None:
        assert list(como_registros([1, 2])) == [{"valor": 1}, {"valor": 2}]


class TestAplanar:
    """El filtro de aplanado resuelve la anidación en nombres de columna."""

    def test_objeto_anidado_usa_el_separador(self) -> None:
        assert aplanar_valor({"a": {"b": 1}}, "") == {"a.b": 1}

    def test_anidacion_de_tres_niveles(self) -> None:
        assert aplanar_valor({"a": {"b": {"c": 3}}}, "") == {"a.b.c": 3}

    def test_separador_personalizado(self) -> None:
        assert aplanar_valor({"a": {"b": 1}}, "", separador="/") == {"a/b": 1}

    def test_lista_se_serializa_como_json(self) -> None:
        assert aplanar_valor({"a": [1, 2]}, "") == {"a": "[1, 2]"}

    def test_objeto_vacio_conserva_la_columna_vacia(self) -> None:
        assert aplanar_valor({"a": {}}, "") == {"a": ""}

    def test_objeto_vacio_en_la_raiz_no_produce_columnas(self) -> None:
        assert aplanar_valor({}, "") == {}

    def test_registros_completos(self) -> None:
        registros = [{"a": {"b": 1}, "c": 2}]
        assert list(aplanar(registros)) == [{"a.b": 1, "c": 2}]


class TestFiltrarCampos:
    """El filtro de campos decide qué información llega a la salida."""

    def test_incluir_conserva_solo_los_campos_pedidos(self) -> None:
        assert list(filtrar_campos([{"a": 1, "b": 2}], incluir=["b"])) == [{"b": 2}]

    def test_incluir_respeta_el_orden_pedido(self) -> None:
        resultado = list(filtrar_campos([{"a": 1, "b": 2}], incluir=["b", "a"]))
        assert list(resultado[0]) == ["b", "a"]

    def test_incluir_rellena_los_campos_ausentes(self) -> None:
        assert list(filtrar_campos([{"a": 1}], incluir=["a", "z"])) == [{"a": 1, "z": ""}]

    def test_excluir_descarta_los_campos_pedidos(self) -> None:
        assert list(filtrar_campos([{"a": 1, "b": 2}], excluir=["b"])) == [{"a": 1}]

    def test_sin_filtros_pasan_todos_los_campos(self) -> None:
        assert list(filtrar_campos([{"a": 1, "b": 2}])) == [{"a": 1, "b": 2}]

    def test_incluir_y_excluir_a_la_vez_es_error(self) -> None:
        with pytest.raises(ValueError) as error:
            list(filtrar_campos([{"a": 1}], incluir=["a"], excluir=["b"]))
        assert "a la vez" in str(error.value)


class TestEncabezado:
    """El cálculo del encabezado es estable y conserva el orden de aparición."""

    def test_union_de_campos_en_orden_de_aparicion(self) -> None:
        assert calcular_encabezado([{"a": 1}, {"b": 2}, {"a": 3}]) == ["a", "b"]

    def test_registros_vacios_dan_encabezado_vacio(self) -> None:
        assert calcular_encabezado([]) == []


class TestEscribirCsv:
    """La etapa de salida produce CSV válido."""

    def test_encabezado_y_filas(self) -> None:
        destino = io.StringIO()
        filas = escribir_csv([{"a": 1, "b": 2}], destino, ",")
        assert filas == 1
        assert destino.getvalue() == "a,b\n1,2\n"

    def test_delimitador_personalizado(self) -> None:
        destino = io.StringIO()
        escribir_csv([{"a": 1, "b": 2}], destino, ";")
        assert destino.getvalue() == "a;b\n1;2\n"

    def test_valores_especiales(self) -> None:
        destino = io.StringIO()
        escribir_csv([{"n": None, "v": True, "f": False}], destino, ",")
        assert destino.getvalue() == "n,v,f\n,true,false\n"

    def test_valor_con_coma_se_entrecomilla(self) -> None:
        destino = io.StringIO()
        escribir_csv([{"a": "uno,dos"}], destino, ",")
        assert destino.getvalue() == 'a\n"uno,dos"\n'

    def test_sin_registros_no_escribe_nada(self) -> None:
        destino = io.StringIO()
        assert escribir_csv([], destino, ",") == 0
        assert destino.getvalue() == ""


class TestConvertir:
    """El pipeline completo, encadenado de punta a punta."""

    def test_conversion_minima(self) -> None:
        destino = io.StringIO()
        filas = convertir('[{"a": 1}]', destino)
        assert filas == 1
        assert destino.getvalue() == "a\n1\n"

    def test_conversion_con_anidacion(self) -> None:
        destino = io.StringIO()
        convertir('[{"a": {"b": 2}}]', destino)
        assert destino.getvalue() == "a.b\n2\n"

    def test_conversion_con_inclusion(self) -> None:
        destino = io.StringIO()
        convertir('[{"a": 1, "b": 2}]', destino, incluir=["a"])
        assert destino.getvalue() == "a\n1\n"

    def test_conversion_con_exclusion(self) -> None:
        destino = io.StringIO()
        convertir('[{"a": 1, "b": 2}]', destino, excluir=["b"])
        assert destino.getvalue() == "a\n1\n"

    def test_conversion_de_json_lines(self) -> None:
        destino = io.StringIO()
        filas = convertir('{"a": 1}\n{"a": 2}\n', destino)
        assert filas == 2
        assert destino.getvalue() == "a\n1\n2\n"

    def test_registros_heterogeneos_completan_columnas(self) -> None:
        destino = io.StringIO()
        convertir('[{"a": 1}, {"b": 2}]', destino)
        assert destino.getvalue() == "a,b\n1,\n,2\n"

    def test_error_de_entrada_propaga_origen(self) -> None:
        with pytest.raises(ErrorDeEntrada):
            convertir("{", io.StringIO(), origen="entrada.json")

    def test_estructura_anidada_compleja_se_aplana_y_serializa(self) -> None:
        destino = io.StringIO()
        convertir(json.dumps([{"a": {"b": [1, {"c": 2}]}}]), destino)
        assert destino.getvalue() == 'a.b\n"[1, {""c"": 2}]"\n'
