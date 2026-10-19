"""Lectura de las métricas reales de test desde los archivos de ``modelo/``.

Ninguna cifra de rendimiento se escribe a mano: todo se lee de los archivos.
"""
from __future__ import annotations

import csv
import json
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)

_ETIQUETAS: dict[str, str] = {
    "n_test": "Imágenes de test",
    "n_clases": "Clases",
    "accuracy_test": "Exactitud (test)",
    "f1_macro_test": "F1 macro (test)",
    "top3_accuracy_test": "Exactitud top-3 (test)",
    "enfermas_predichas_sanas_test": "Hojas enfermas predichas como sanas (test)",
    "enfermas_test": "Hojas enfermas en test",
    "accuracy_val": "Exactitud (validación)",
    "f1_macro_val": "F1 macro (validación)",
}


def cargar_metricas() -> dict[str, Any]:
    return json.loads(config.RUTA_METRICAS.read_text(encoding="utf-8"))


def _formatear(clave: str, valor: Any) -> str:
    if isinstance(valor, float) and 0.0 <= valor <= 1.0:
        return f"{valor * 100:.2f} %".replace(".", ",")
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def metricas_en_filas() -> list[list[str]]:
    """Pares [métrica, valor] legibles para mostrar en tablas."""
    return [[_ETIQUETAS.get(k, k), _formatear(k, v)] for k, v in cargar_metricas().items()]


def cargar_reporte_por_clase() -> tuple[list[str], list[list[str]]]:
    """Cabecera y filas de ``reporte_test_por_clase.csv`` (la primera columna es la clase)."""
    with config.RUTA_REPORTE_CLASES.open(encoding="utf-8", newline="") as f:
        filas = list(csv.reader(f))
    cabecera = ["clase", *filas[0][1:]]
    return cabecera, filas[1:]
