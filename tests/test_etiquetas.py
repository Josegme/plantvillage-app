"""(b) Las etiquetas cubren las 38 clases del modelo."""
from __future__ import annotations

import json

import pytest

import config
import etiquetas


@pytest.fixture(scope="module")
def clases() -> list[str]:
    return json.loads(config.RUTA_CLASES.read_text(encoding="utf-8"))


def test_hay_38_clases(clases: list[str]) -> None:
    assert len(clases) == config.NUM_CLASES == 38
    assert len(set(clases)) == 38


def test_todas_las_clases_tienen_traduccion(clases: list[str]) -> None:
    for clase in clases:
        assert etiquetas.cultivo_es(clase)
        assert etiquetas.estado_es(clase)
        assert etiquetas.nombre_legible(clase)


def test_no_hay_entradas_sobrantes_en_los_diccionarios(clases: list[str]) -> None:
    cultivos = {etiquetas.separar(c)[0] for c in clases}
    estados = {etiquetas.separar(c)[1] for c in clases}
    assert set(etiquetas.CULTIVOS) == cultivos
    assert set(etiquetas.ESTADOS) == estados


def test_nombre_legible_ejemplo() -> None:
    assert etiquetas.nombre_legible("Tomato___Early_blight") == "Tomate — Tizón temprano"
    assert etiquetas.es_sana("Apple___healthy")
    assert not etiquetas.es_sana("Apple___Black_rot")


@pytest.mark.parametrize("clase", ["", "SinSeparador", "Tomato___", "___x", "Alien___healthy", "Tomato___inventada"])
def test_clase_invalida_falla_de_forma_explicita(clase: str) -> None:
    with pytest.raises(etiquetas.ClaseDesconocida):
        etiquetas.nombre_legible(clase)
