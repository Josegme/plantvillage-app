"""Historial de consultas en SQLite (stdlib).

Solo se guardan metadatos: marca de tiempo UTC, top-1, confianza, flag de
"no concluyente", latencia y un SHA-256 truncado de los bytes de la imagen.
NUNCA se guarda la imagen ni datos del usuario.
"""
from __future__ import annotations

import csv
import io
import logging
import sqlite3
import threading
from collections.abc import Iterable, Sequence
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import config

logger = logging.getLogger(__name__)

COLUMNAS: tuple[str, ...] = (
    "id",
    "timestamp_utc",
    "top1",
    "confianza",
    "no_concluyente",
    "latencia_ms",
    "hash_imagen",
)

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc  TEXT    NOT NULL,
    top1           TEXT    NOT NULL,
    confianza      REAL    NOT NULL,
    no_concluyente INTEGER NOT NULL CHECK (no_concluyente IN (0, 1)),
    latencia_ms    REAL    NOT NULL,
    hash_imagen    TEXT    NOT NULL
)
"""

# Caracteres que un programa de hojas de cálculo interpreta como inicio de fórmula.
_INICIOS_DE_FORMULA: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")

Fila = tuple[int, str, str, float, int, float, str]


def neutralizar_celda(valor: object) -> object:
    """Prefija con ``'`` los textos que empiezan por =, +, -, @, tabulador o retorno de carro."""
    if isinstance(valor, str) and valor.startswith(_INICIOS_DE_FORMULA):
        return "'" + valor
    return valor


def a_csv(filas: Iterable[Sequence[object]]) -> str:
    """Serializa filas del historial a CSV neutralizando la inyección de fórmulas."""
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS)
    for fila in filas:
        escritor.writerow([neutralizar_celda(celda) for celda in fila])
    return salida.getvalue()


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class Historial:
    def __init__(self, ruta: Path | str = config.RUTA_HISTORIAL) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._escritura = threading.Lock()
        with closing(self._conectar()) as con, con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute(_ESQUEMA)

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.ruta, timeout=10)

    def registrar(
        self,
        top1: str,
        confianza: float,
        no_concluyente: bool,
        latencia_ms: float,
        hash_imagen: str,
        ahora: datetime | None = None,
    ) -> None:
        marca = (ahora or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._escritura, closing(self._conectar()) as con, con:
            con.execute(
                "INSERT INTO consultas (timestamp_utc, top1, confianza, no_concluyente, latencia_ms, hash_imagen)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (marca, top1, float(confianza), int(bool(no_concluyente)), float(latencia_ms), hash_imagen),
            )

    def consultar(
        self,
        texto: str | None = None,
        solo_no_concluyentes: bool = False,
        limite: int = config.MAX_FILAS_HISTORIAL,
    ) -> list[Fila]:
        """Filas más recientes primero. ``texto`` filtra por clase top-1 o por hash (subcadena)."""
        condiciones: list[str] = []
        parametros: list[object] = []
        if texto and texto.strip():
            patron = f"%{_escapar_like(texto.strip())}%"
            condiciones.append("(top1 LIKE ? ESCAPE '\\' OR hash_imagen LIKE ? ESCAPE '\\')")
            parametros += [patron, patron]
        if solo_no_concluyentes:
            condiciones.append("no_concluyente = 1")
        where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
        limite = max(1, min(int(limite), config.MAX_FILAS_HISTORIAL))
        consulta = f"SELECT {', '.join(COLUMNAS)} FROM consultas{where} ORDER BY id DESC LIMIT ?"
        with closing(self._conectar()) as con:
            return [tuple(f) for f in con.execute(consulta, [*parametros, limite]).fetchall()]  # type: ignore[misc]

    def contar(self) -> int:
        with closing(self._conectar()) as con:
            return int(con.execute("SELECT COUNT(*) FROM consultas").fetchone()[0])
