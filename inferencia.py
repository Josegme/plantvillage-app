"""Carga única del modelo y predicción."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Hipotesis:
    indice: int
    clase: str
    confianza: float


@dataclass(frozen=True)
class Prediccion:
    hipotesis: tuple[Hipotesis, ...]  # ordenadas de mayor a menor confianza
    latencia_ms: float

    @property
    def top1(self) -> Hipotesis:
        return self.hipotesis[0]


def validar_umbral(umbral: float) -> float:
    """Devuelve el umbral como float en [0, 1] o lanza ValueError."""
    try:
        valor = float(umbral)
    except (TypeError, ValueError):
        raise ValueError("El umbral debe ser un número.") from None
    if math.isnan(valor) or not 0.0 <= valor <= 1.0:
        raise ValueError("El umbral debe estar entre 0 y 1.")
    return valor


def es_concluyente(confianza: float, umbral: float) -> bool:
    """Un resultado es concluyente si la confianza top-1 alcanza el umbral (>=)."""
    return confianza >= validar_umbral(umbral)


class Clasificador:
    """Envuelve el modelo Keras. Se instancia una sola vez (ver ``obtener_clasificador``)."""

    def __init__(
        self,
        ruta_modelo: Path = config.RUTA_MODELO,
        ruta_clases: Path = config.RUTA_CLASES,
        calentar: bool = True,
    ) -> None:
        import keras  # import diferido hasta que realmente se necesita el modelo

        self.ruta_modelo = Path(ruta_modelo)
        self.clases: list[str] = json.loads(Path(ruta_clases).read_text(encoding="utf-8"))
        # safe_mode se mantiene en su valor por defecto (True).
        self._modelo = keras.saving.load_model(self.ruta_modelo, compile=False)
        salida = self._modelo.output_shape[-1]
        if salida != len(self.clases):
            raise RuntimeError(f"El modelo tiene {salida} salidas y class_names.json {len(self.clases)} clases.")
        self._lock = threading.Lock()
        self.version_modelo = self._calcular_version()
        if calentar:
            self.predecir_probabilidades(np.zeros((1, config.TAM_ENTRADA, config.TAM_ENTRADA, 3), "float32"))
        logger.info("Modelo cargado (versión %s, %d clases).", self.version_modelo, len(self.clases))

    def _calcular_version(self) -> str:
        sha = hashlib.sha256(self.ruta_modelo.read_bytes()).hexdigest()[:12]
        return f"{self.ruta_modelo.stem}@{sha}"

    def predecir_probabilidades(self, x: np.ndarray) -> np.ndarray:
        """Vector softmax (38,) para un lote de una imagen (1, 224, 224, 3) float32 crudo 0–255."""
        with self._lock:
            salida = self._modelo(x, training=False)
        return np.asarray(salida)[0].astype("float64")

    def predecir(self, x: np.ndarray, k: int = config.TOP_K) -> Prediccion:
        inicio = time.perf_counter()
        probas = self.predecir_probabilidades(x)
        latencia_ms = (time.perf_counter() - inicio) * 1000.0
        indices = np.argsort(-probas, kind="stable")[:k]
        hipotesis = tuple(Hipotesis(int(i), self.clases[int(i)], float(probas[int(i)])) for i in indices)
        return Prediccion(hipotesis=hipotesis, latencia_ms=latencia_ms)

    def info(self) -> dict[str, str]:
        import keras
        import tensorflow as tf

        return {
            "modelo": self.version_modelo,
            "keras": keras.__version__,
            "tensorflow": tf.__version__,
            "clases": str(len(self.clases)),
        }


_instancia: Clasificador | None = None
_lock_instancia = threading.Lock()


def obtener_clasificador() -> Clasificador:
    """Singleton del clasificador. app.py lo invoca al arrancar (carga + calentamiento)."""
    global _instancia
    with _lock_instancia:
        if _instancia is None:
            _instancia = Clasificador()
        return _instancia
