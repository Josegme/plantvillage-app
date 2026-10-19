"""Traducción al español de los nombres de clase de PlantVillage.

Las clases tienen el formato ``Cultivo___Enfermedad`` (tres guiones bajos).
"""
from __future__ import annotations

SEPARADOR = "___"
ESTADO_SANO = "healthy"

CULTIVOS: dict[str, str] = {
    "Apple": "Manzana",
    "Blueberry": "Arándano",
    "Cherry_(including_sour)": "Cereza",
    "Corn_(maize)": "Maíz",
    "Grape": "Uva",
    "Orange": "Naranja",
    "Peach": "Durazno",
    "Pepper,_bell": "Pimiento",
    "Potato": "Papa",
    "Raspberry": "Frambuesa",
    "Soybean": "Soja",
    "Squash": "Calabaza",
    "Strawberry": "Fresa",
    "Tomato": "Tomate",
}

ESTADOS: dict[str, str] = {
    ESTADO_SANO: "Sana",
    "Apple_scab": "Sarna del manzano",
    "Black_rot": "Podredumbre negra",
    "Cedar_apple_rust": "Roya del cedro y el manzano",
    "Powdery_mildew": "Oídio",
    "Cercospora_leaf_spot Gray_leaf_spot": "Mancha foliar por Cercospora (mancha gris)",
    "Common_rust_": "Roya común",
    "Northern_Leaf_Blight": "Tizón foliar del norte",
    "Esca_(Black_Measles)": "Esca (sarampión negro)",
    "Leaf_blight_(Isariopsis_Leaf_Spot)": "Tizón foliar (mancha de Isariopsis)",
    "Haunglongbing_(Citrus_greening)": "Huanglongbing (enverdecimiento de los cítricos)",
    "Bacterial_spot": "Mancha bacteriana",
    "Early_blight": "Tizón temprano",
    "Late_blight": "Tizón tardío",
    "Leaf_scorch": "Quemadura de la hoja",
    "Leaf_Mold": "Moho de la hoja",
    "Septoria_leaf_spot": "Mancha foliar por Septoria",
    "Spider_mites Two-spotted_spider_mite": "Ácaros (araña roja de dos manchas)",
    "Target_Spot": "Mancha en diana",
    "Tomato_Yellow_Leaf_Curl_Virus": "Virus del rizado amarillo de la hoja del tomate",
    "Tomato_mosaic_virus": "Virus del mosaico del tomate",
}


class ClaseDesconocida(KeyError):
    """La clase no figura en el diccionario de traducción."""


def separar(clase: str) -> tuple[str, str]:
    """Separa ``Cultivo___Enfermedad`` en ``(cultivo, estado)`` sin traducir."""
    cultivo, sep, estado = clase.partition(SEPARADOR)
    if not sep or not cultivo or not estado:
        raise ClaseDesconocida(f"Formato de clase no válido: {clase!r}")
    return cultivo, estado


def cultivo_es(clase: str) -> str:
    cultivo, _ = separar(clase)
    try:
        return CULTIVOS[cultivo]
    except KeyError:
        raise ClaseDesconocida(f"Cultivo sin traducción: {cultivo!r}") from None


def estado_es(clase: str) -> str:
    _, estado = separar(clase)
    try:
        return ESTADOS[estado]
    except KeyError:
        raise ClaseDesconocida(f"Estado sin traducción: {estado!r}") from None


def es_sana(clase: str) -> bool:
    return separar(clase)[1] == ESTADO_SANO


def nombre_legible(clase: str) -> str:
    """Devuelve p. ej. ``Tomate — Tizón temprano`` para ``Tomato___Early_blight``."""
    return f"{cultivo_es(clase)} — {estado_es(clase)}"
