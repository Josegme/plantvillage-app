"""(c) Lógica del umbral de confianza."""
from __future__ import annotations

import math

import pytest

import config
from inferencia import es_concluyente, validar_umbral


def test_umbral_por_defecto() -> None:
    assert config.UMBRAL_CONFIANZA_DEFECTO == 0.60


@pytest.mark.parametrize(
    ("confianza", "umbral", "esperado"),
    [
        (0.95, 0.60, True),
        (0.60, 0.60, True),  # el límite es inclusivo
        (0.5999, 0.60, False),
        (0.0, 0.60, False),
        (1.0, 1.0, True),
        (0.99, 1.0, False),
        (0.0, 0.0, True),
    ],
)
def test_es_concluyente(confianza: float, umbral: float, esperado: bool) -> None:
    assert es_concluyente(confianza, umbral) is esperado


@pytest.mark.parametrize("malo", [-0.1, 1.01, math.nan, math.inf, "abc", None])
def test_umbral_invalido_se_rechaza(malo: object) -> None:
    with pytest.raises(ValueError):
        validar_umbral(malo)  # type: ignore[arg-type]


def test_umbral_numerico_en_texto_se_acepta() -> None:
    assert validar_umbral("0.75") == 0.75
