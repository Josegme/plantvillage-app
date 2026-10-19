"""Textos largos de la interfaz (carpeta ``contenido/``) con las cifras leídas de los archivos.

Los textos están en Markdown para poder editarlos sin tocar código. Las cifras de
rendimiento NO se escriben a mano: aparecen como marcadores ``{{nombre}}`` que se
rellenan con ``modelo/metricas_test.json`` y ``modelo/reporte_test_por_clase.csv``.
"""
from __future__ import annotations

import re

import config
import etiquetas
import metricas

DIR_CONTENIDO = config.BASE_DIR / "contenido"
_MARCADOR = re.compile(r"\{\{(\w+)\}\}")


def _pct(valor: float, decimales: int = 2) -> str:
    return f"{valor * 100:.{decimales}f} %".replace(".", ",")


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def valores() -> dict[str, str]:
    """Marcadores disponibles y su valor, calculados desde los archivos de ``modelo/``."""
    m = metricas.cargar_metricas()
    debiles = metricas.clases_con_menor_recall(4)
    return {
        "n_test": _miles(m["n_test"]),
        "exactitud_test": _pct(m["accuracy_test"]),
        "f1_macro_test": _pct(m["f1_macro_test"]),
        "top3_test": _pct(m["top3_accuracy_test"]),
        "enfermas_sanas": str(m["enfermas_predichas_sanas_test"]),
        "enfermas_test": _miles(m["enfermas_test"]),
        "debiles": ", ".join(f"{etiquetas.nombre_legible(c).replace(' — ', ' (')})" for c, _ in debiles),
    }


def renderizar(texto: str, datos: dict[str, str] | None = None) -> str:
    """Sustituye cada ``{{marcador}}``; lanza ``KeyError`` si alguno no tiene valor."""
    datos = datos if datos is not None else valores()
    return _MARCADOR.sub(lambda m: datos[m.group(1)], texto)


def cargar(nombre: str) -> str:
    """Lee ``contenido/<nombre>.md`` y rellena sus marcadores."""
    return renderizar((DIR_CONTENIDO / f"{nombre}.md").read_text(encoding="utf-8"))
