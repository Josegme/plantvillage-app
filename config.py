"""Configuración central: umbral, límites, rutas y variables de entorno.

Este módulo debe importarse antes que TensorFlow y Gradio: fija variables de
entorno (nivel de logs, analítica, directorio temporal) que esas librerías leen
al importarse.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent
MODELO_DIR: Path = BASE_DIR / "modelo"
DATA_DIR: Path = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))

# Directorio temporal propio para las subidas de Gradio (ver app.py). Debe fijarse
# antes de importar gradio.
GRADIO_TMP_DIR: Path = DATA_DIR / "gradio_tmp"
GRADIO_TMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("GRADIO_TEMP_DIR", str(GRADIO_TMP_DIR))
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

# --- Modelo y artefactos (solo lectura) ---
RUTA_MODELO: Path = MODELO_DIR / "plantvillage_mobilenetv2.keras"
RUTA_CLASES: Path = MODELO_DIR / "class_names.json"
RUTA_METRICAS: Path = MODELO_DIR / "metricas_test.json"
RUTA_REPORTE_CLASES: Path = MODELO_DIR / "reporte_test_por_clase.csv"
RUTA_MATRIZ_CONFUSION: Path = MODELO_DIR / "matriz_confusion_test.png"
DIR_EJEMPLOS: Path = MODELO_DIR / "ejemplos"

TAM_ENTRADA: int = 224
NUM_CLASES: int = 38
TOP_K: int = 3

# --- Inferencia ---
UMBRAL_CONFIANZA_DEFECTO: float = 0.60

# --- Validación de entradas ---
MAX_BYTES: int = 5 * 1024 * 1024
MAX_PIXELES: int = 30_000_000  # protección frente a decompression bombs
FORMATOS_PERMITIDOS: frozenset[str] = frozenset({"JPEG", "PNG", "WEBP"})
EXTENSIONES_PERMITIDAS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# --- Historial ---
RUTA_HISTORIAL: Path = Path(os.environ.get("HISTORIAL_DB", DATA_DIR / "historial.db"))
LONGITUD_HASH: int = 16  # caracteres hexadecimales del SHA-256 que se guardan
MAX_FILAS_HISTORIAL: int = 5000

# --- Administración ---
VAR_PASSWORD_ADMIN: str = "ADMIN_PASSWORD"
TTL_TOKEN_SEGUNDOS: int = 3600
MAX_TOKENS_ACTIVOS: int = 50
INTENTOS_ANTES_DE_BLOQUEO: int = 3
BACKOFF_BASE_SEGUNDOS: int = 5
BACKOFF_MAX_SEGUNDOS: int = 900

# --- Privacidad de archivos temporales de Gradio ---
# (frecuencia de barrido, antigüedad máxima) en segundos, para gr.Blocks(delete_cache=...)
DELETE_CACHE: tuple[int, int] = (60, 300)

REPOSITORIO_URL: str = "https://github.com/Josegme/plantvillage-app"
