"""(a) El preprocesado reproduce la predicción esperada sobre modelo/ejemplos/.

Fuentes de verdad, de más a menos independiente:

1. ``modelo/ejemplos_referencia.json``: generado con el pipeline de evaluación en Colab.
2. Una ruta de decodificación independiente (``tf.io.decode_image``) comparada píxel a píxel.
3. ``tests/instantanea_local.json``: INSTANTÁNEA generada con este mismo código. Sirve
   para detectar regresiones, no es una validación independiente.

Sobre las tolerancias (medidas con tensorflow-cpu 2.21.0 / keras 3.13.2 en Windows):

* La referencia de Colab coincide con la ruta ``tf.io.decode_image`` hasta el 4.º decimal
  (la referencia está redondeada a 4 decimales: error de redondeo <= 5e-5). Por eso esa
  ruta se exige con ``TOL_REDONDEO = 1e-4``: demuestra que modelo, pesos y versiones
  reproducen la evaluación.
* El preprocesado de producción (PIL para decodificar + ``tf.image.resize``) difiere del
  decodificador JPEG de TensorFlow (diferencias de hasta ~4 niveles de intensidad por
  imagen) y eso mueve la confianza hasta 0,0075 (Tomato_Early_blight). Se acepta
  ``TOL_DECODIFICADOR = 0.01`` (máximo medido x1,3) para la comparación de confianzas.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import config
import preprocesado
from inferencia import Clasificador

RUTA_REFERENCIA = config.MODELO_DIR / "ejemplos_referencia.json"
RUTA_INSTANTANEA = Path(__file__).parent / "instantanea_local.json"

TOL_REDONDEO = 1e-4
TOL_DECODIFICADOR = 0.01
TOL_INSTANTANEA = 1e-4
# Diferencia máxima de píxel entre decodificadores (medida: 3,3–3,9) y mínima al cambiar
# el remuestreo a PIL.resize (medida: 9,2–23,7). El umbral queda entre ambas.
UMBRAL_PIXEL_REMUESTREO = 6.0


@pytest.fixture(scope="session")
def clasificador() -> Clasificador:
    return Clasificador()


@pytest.fixture(scope="session")
def referencia() -> dict:
    return json.loads(RUTA_REFERENCIA.read_text(encoding="utf-8"))


def _tensor(ruta: Path) -> np.ndarray:
    return preprocesado.preprocesar(preprocesado.decodificar(preprocesado.leer_bytes(ruta)))


def _ejemplos() -> list[Path]:
    return sorted(config.DIR_EJEMPLOS.glob("*.jpg"))


def _tensor_tfio(ruta: Path) -> np.ndarray:
    import tensorflow as tf

    img = tf.io.decode_image(tf.io.read_file(str(ruta)), channels=3, expand_animations=False)
    return tf.image.resize(img, (config.TAM_ENTRADA, config.TAM_ENTRADA)).numpy()[None].astype("float32")


def _tensor_pil_resize(ruta: Path) -> np.ndarray:
    img = Image.open(ruta).convert("RGB").resize((config.TAM_ENTRADA, config.TAM_ENTRADA))
    return np.array(img)[None].astype("float32")


def test_hay_8_ejemplos_y_referencia_completa(referencia: dict) -> None:
    assert len(_ejemplos()) == 8
    assert {p.name for p in _ejemplos()} == set(referencia)


@pytest.mark.parametrize("ruta", _ejemplos(), ids=lambda p: p.name)
def test_contrato_del_tensor(ruta: Path) -> None:
    x = _tensor(ruta)
    assert x.shape == (1, config.TAM_ENTRADA, config.TAM_ENTRADA, 3)
    assert x.dtype == np.float32
    assert 0.0 <= x.min() and x.max() <= 255.0
    assert x.max() > 1.0, "los valores deben ser crudos 0–255: no se normaliza fuera del modelo"


def test_orientacion_exif_se_aplica() -> None:
    """Una foto con EXIF Orientation=6 se preprocesa igual que la imagen ya rotada."""
    base = Image.linear_gradient("L").convert("RGB").crop((0, 0, 256, 128))
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = io.BytesIO()
    base.save(buf, format="PNG", exif=exif)
    con_exif = preprocesado.decodificar(buf.getvalue())
    esperado = preprocesado.preprocesar(base.transpose(Image.Transpose.ROTATE_270))
    assert np.array_equal(preprocesado.preprocesar(con_exif), esperado)


@pytest.mark.parametrize("ruta", _ejemplos(), ids=lambda p: p.name)
def test_ruta_independiente_difiere_solo_por_el_decodificador(ruta: Path) -> None:
    dif = np.abs(_tensor(ruta) - _tensor_tfio(ruta))
    assert dif.max() < UMBRAL_PIXEL_REMUESTREO, f"max |dif| de píxel = {dif.max():.2f}"


@pytest.mark.parametrize("ruta", _ejemplos(), ids=lambda p: p.name)
def test_pil_resize_se_detecta_a_nivel_de_pixel(ruta: Path) -> None:
    """Cambiar el remuestreo a PIL.resize produce un tensor claramente distinto.

    Se verifica a nivel de píxel. A nivel de confianza NO se fuerza: en varias imágenes
    la salida del modelo cae dentro de la tolerancia aunque el tensor sea distinto.
    """
    dif = np.abs(_tensor(ruta) - _tensor_pil_resize(ruta))
    assert dif.max() > UMBRAL_PIXEL_REMUESTREO, f"max |dif| de píxel = {dif.max():.2f}"


@pytest.mark.parametrize("nombre", sorted(json.loads(RUTA_REFERENCIA.read_text(encoding="utf-8"))))
def test_prediccion_coincide_con_referencia_de_colab(clasificador: Clasificador, referencia: dict, nombre: str) -> None:
    ref = referencia[nombre]
    pred = clasificador.predecir(_tensor(config.DIR_EJEMPLOS / nombre))
    assert pred.top1.clase == ref["top1"]
    assert [h.clase for h in pred.hipotesis] == [h["clase"] for h in ref["top3"]]
    for hip, esperado in zip(pred.hipotesis, ref["top3"]):
        assert hip.confianza == pytest.approx(esperado["confianza"], abs=TOL_DECODIFICADOR)
    assert pred.top1.confianza == pytest.approx(ref["confianza_top1"], abs=TOL_DECODIFICADOR)


@pytest.mark.parametrize("nombre", sorted(json.loads(RUTA_REFERENCIA.read_text(encoding="utf-8"))))
def test_entorno_reproduce_la_referencia_con_el_decodificador_de_tf(
    clasificador: Clasificador, referencia: dict, nombre: str
) -> None:
    """Con la decodificación de TF las confianzas coinciden con Colab hasta el redondeo."""
    ref = referencia[nombre]
    probas = clasificador.predecir_probabilidades(_tensor_tfio(config.DIR_EJEMPLOS / nombre))
    for esperado in ref["top3"]:
        obtenido = float(probas[clasificador.clases.index(esperado["clase"])])
        assert obtenido == pytest.approx(esperado["confianza"], abs=TOL_REDONDEO)


@pytest.mark.parametrize("nombre", sorted(json.loads(RUTA_REFERENCIA.read_text(encoding="utf-8"))))
def test_instantanea_local_no_es_validacion_independiente(clasificador: Clasificador, nombre: str) -> None:
    """INSTANTÁNEA generada por este código: detecta cambios, no demuestra corrección."""
    esperado = json.loads(RUTA_INSTANTANEA.read_text(encoding="utf-8"))[nombre]
    pred = clasificador.predecir(_tensor(config.DIR_EJEMPLOS / nombre))
    assert [h.clase for h in pred.hipotesis] == [e["clase"] for e in esperado]
    for hip, e in zip(pred.hipotesis, esperado):
        assert hip.confianza == pytest.approx(e["confianza"], abs=TOL_INSTANTANEA)
