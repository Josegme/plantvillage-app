"""(f) El CSV exportado neutraliza fórmulas, y pruebas del historial."""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

import historial
from historial import Historial, a_csv, neutralizar_celda


@pytest.mark.parametrize("peligroso", ["=1+1", "+cmd|' /C calc'!A0", "-2+3", "@SUM(A1)", "\t=1", "\r=1", '=HYPERLINK("http://x")'])
def test_neutraliza_inicios_de_formula(peligroso: str) -> None:
    assert neutralizar_celda(peligroso) == "'" + peligroso


@pytest.mark.parametrize("seguro", ["Tomato___healthy", "", "a=b", "x+y", " =1", "12.5"])
def test_no_toca_textos_seguros(seguro: str) -> None:
    assert neutralizar_celda(seguro) == seguro


def test_numeros_no_se_modifican() -> None:
    assert neutralizar_celda(0.5) == 0.5
    assert neutralizar_celda(3) == 3


def test_csv_exportado_neutraliza_celdas_peligrosas(tmp_path: Path) -> None:
    repo = Historial(tmp_path / "h.db")
    repo.registrar("=cmd|' /C calc'!A0", 0.9, False, 10.0, "+aaaaaaaaaaaaaaa")
    repo.registrar("@SUM(1)", 0.8, True, 11.0, "-bbbbbbbbbbbbbbb")
    repo.registrar("Tomato___healthy", 0.99, False, 9.0, "0123456789abcdef")
    contenido = a_csv(repo.consultar())
    celdas = [c for fila in csv.reader(io.StringIO(contenido)) for c in fila]
    assert all(not c.startswith(historial._INICIOS_DE_FORMULA) for c in celdas[len(historial.COLUMNAS):])
    assert "'=cmd|' /C calc'!A0" in celdas and "'@SUM(1)" in celdas
    assert "'+aaaaaaaaaaaaaaa" in celdas and "'-bbbbbbbbbbbbbbb" in celdas
    assert "Tomato___healthy" in celdas


def test_csv_tiene_cabecera_y_una_fila_por_registro(tmp_path: Path) -> None:
    repo = Historial(tmp_path / "h.db")
    for i in range(3):
        repo.registrar("Apple___healthy", 0.9, False, 5.0, f"{i:016x}")
    filas = list(csv.reader(io.StringIO(a_csv(repo.consultar()))))
    assert tuple(filas[0]) == historial.COLUMNAS
    assert len(filas) == 4


# --- historial ---
def test_solo_se_guardan_metadatos(tmp_path: Path) -> None:
    ruta = tmp_path / "h.db"
    Historial(ruta).registrar("Apple___healthy", 0.9, False, 5.0, "0123456789abcdef")
    con = sqlite3.connect(ruta)
    columnas = [c[1] for c in con.execute("PRAGMA table_info(consultas)")]
    con.close()
    assert columnas == list(historial.COLUMNAS)
    assert not any(tipo in c for c in columnas for tipo in ("imagen_bytes", "blob", "nombre", "ruta", "usuario", "ip"))


def test_registro_y_consulta(tmp_path: Path) -> None:
    repo = Historial(tmp_path / "h.db")
    repo.registrar("Tomato___Early_blight", 0.55, True, 20.0, "aaaa0000bbbb1111", ahora=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    repo.registrar("Apple___healthy", 0.97, False, 10.0, "cccc2222dddd3333")
    assert repo.contar() == 2
    todas = repo.consultar()
    assert [f[2] for f in todas] == ["Apple___healthy", "Tomato___Early_blight"]  # más reciente primero
    assert todas[1][1] == "2026-01-02T03:04:05Z"
    assert [f[2] for f in repo.consultar("tomato")] == ["Tomato___Early_blight"]
    assert [f[2] for f in repo.consultar("cccc2222")] == ["Apple___healthy"]
    assert [f[2] for f in repo.consultar(solo_no_concluyentes=True)] == ["Tomato___Early_blight"]


def test_filtro_no_es_vulnerable_a_inyeccion_sql(tmp_path: Path) -> None:
    repo = Historial(tmp_path / "h.db")
    repo.registrar("Apple___healthy", 0.97, False, 10.0, "cccc2222dddd3333")
    assert repo.consultar("'; DROP TABLE consultas; --") == []
    assert repo.consultar("%") == []  # comodines escapados: no coincide con todo
    assert repo.contar() == 1
