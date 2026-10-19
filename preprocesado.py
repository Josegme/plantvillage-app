"""Validación de entradas y preprocesado de imágenes.

El preprocesado de ``preprocesar`` es el de referencia validado contra la
evaluación del modelo. NO normalizar aquí: el reescalado a [-1, 1] ya está
dentro del modelo (entrada: float32 crudo 0–255).
"""
from __future__ import annotations

import hashlib
import io
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

import config

Image.MAX_IMAGE_PIXELS = config.MAX_PIXELES


class EntradaInvalida(ValueError):
    """La imagen no cumple las validaciones; el mensaje es apto para el usuario."""


def leer_bytes(ruta: str | Path) -> bytes:
    """Lee el archivo comprobando extensión y tamaño máximo, sin cargarlo entero si excede."""
    ruta = Path(ruta)
    if ruta.suffix.lower() not in config.EXTENSIONES_PERMITIDAS:
        raise EntradaInvalida("Formato no admitido. Usa una imagen JPG, JPEG, PNG o WEBP.")
    try:
        with ruta.open("rb") as f:
            datos = f.read(config.MAX_BYTES + 1)
    except OSError:
        raise EntradaInvalida("No se pudo leer el archivo subido.") from None
    if not datos:
        raise EntradaInvalida("El archivo está vacío.")
    if len(datos) > config.MAX_BYTES:
        raise EntradaInvalida(f"La imagen supera el máximo de {config.MAX_BYTES // (1024 * 1024)} MB.")
    return datos


def hash_bytes(datos: bytes) -> str:
    """SHA-256 truncado de los bytes de la imagen (único dato derivado de ella que se guarda)."""
    return hashlib.sha256(datos).hexdigest()[: config.LONGITUD_HASH]


def decodificar(datos: bytes) -> Image.Image:
    """Decodifica comprobando formato real, límite de píxeles e integridad."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(datos))
            if img.format not in config.FORMATOS_PERMITIDOS:
                raise EntradaInvalida("Formato no admitido. Usa una imagen JPG, JPEG, PNG o WEBP.")
            ancho, alto = img.size
            if ancho < 1 or alto < 1:
                raise EntradaInvalida("La imagen no tiene dimensiones válidas.")
            if ancho * alto > config.MAX_PIXELES:
                raise EntradaInvalida("La imagen tiene demasiados píxeles. Reduce su resolución.")
            img.load()
    except EntradaInvalida:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise EntradaInvalida("La imagen tiene demasiados píxeles. Reduce su resolución.") from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError):
        raise EntradaInvalida("No se pudo leer la imagen: el archivo está dañado o no es una imagen.") from None
    return img


def preprocesar(img: Image.Image) -> np.ndarray:
    """Preprocesado de referencia. Devuelve un tensor (1, 224, 224, 3) float32 con valores 0–255."""
    import tensorflow as tf  # import diferido: acelera los módulos que no lo necesitan

    img = ImageOps.exif_transpose(img).convert("RGB")
    arr = tf.image.resize(np.array(img), (config.TAM_ENTRADA, config.TAM_ENTRADA)).numpy()
    return arr[None, ...].astype("float32")
