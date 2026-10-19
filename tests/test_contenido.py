"""Textos explicativos: marcadores resueltos desde los archivos de modelo/ y sin cifras a mano."""
from __future__ import annotations

import re

import pytest

import config
import contenido
import metricas

TEXTOS = ["para_que_sirve", "como_se_hizo"]
MARCADOR = re.compile(r"\{\{(\w+)\}\}")


@pytest.mark.parametrize("nombre", TEXTOS)
def test_todos_los_marcadores_tienen_valor(nombre: str) -> None:
    crudo = (contenido.DIR_CONTENIDO / f"{nombre}.md").read_text(encoding="utf-8")
    usados = set(MARCADOR.findall(crudo))
    assert usados, "se esperaban marcadores con las cifras de rendimiento"
    assert usados <= set(contenido.valores())
    assert "{{" not in contenido.cargar(nombre)


def test_las_cifras_salen_de_metricas_test_json() -> None:
    m = metricas.cargar_metricas()
    v = contenido.valores()
    assert v["n_test"] == f"{m['n_test']:,}".replace(",", ".")
    assert v["exactitud_test"] == f"{m['accuracy_test'] * 100:.2f} %".replace(".", ",")
    assert v["enfermas_sanas"] == str(m["enfermas_predichas_sanas_test"])


@pytest.mark.parametrize("nombre", TEXTOS)
def test_no_hay_porcentajes_de_rendimiento_escritos_a_mano(nombre: str) -> None:
    """Los únicos % permitidos en el texto crudo son valores de configuración (umbral por defecto)."""
    crudo = (contenido.DIR_CONTENIDO / f"{nombre}.md").read_text(encoding="utf-8")
    porcentajes = re.findall(r"\d+(?:[.,]\d+)?\s?%", crudo)
    assert set(porcentajes) <= {f"{int(config.UMBRAL_CONFIANZA_DEFECTO * 100)} %"}, porcentajes


def test_marcador_desconocido_falla_de_forma_explicita() -> None:
    with pytest.raises(KeyError):
        contenido.renderizar("cifra: {{no_existe}}", {"otro": "1"})


def test_la_pagina_se_puede_leer_en_orden() -> None:
    texto = contenido.cargar("como_se_hizo")
    pasos = re.findall(r"^### (\d+)\. ", texto, flags=re.MULTILINE)
    assert pasos == [str(i) for i in range(1, 12)], "los pasos deben ir numerados 1..11 sin saltos"
    assert texto.count("**Qué se hizo.**") == 11 and texto.count("**Por qué.**") == 11
