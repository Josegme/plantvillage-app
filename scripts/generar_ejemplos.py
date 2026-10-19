"""Calcula con el modelo y el preprocesado de la app las predicciones de los 8 ejemplos.

Salida: ``contenido/ejemplos_demo.json``. La página de proyecto (``docs/``) lo usa para mostrar
resultados REALES sin cargar el modelo en el navegador. Se ejecuta una vez y solo hace falta
repetirlo si cambian el modelo o el preprocesado:

    python scripts/generar_ejemplos.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
import preprocesado  # noqa: E402
from inferencia import Clasificador  # noqa: E402

SALIDA = config.BASE_DIR / "contenido" / "ejemplos_demo.json"


def main() -> None:
    clasificador = Clasificador()
    resultados: dict[str, dict] = {
        "_aviso": (
            "Predicciones calculadas con modelo/plantvillage_mobilenetv2.keras y el preprocesado de la app. "
            "Generado por scripts/generar_ejemplos.py."
        ),
        "_modelo": clasificador.version_modelo,
    }
    for ruta in sorted(config.DIR_EJEMPLOS.glob("*.jpg")):
        x = preprocesado.preprocesar(preprocesado.decodificar(preprocesado.leer_bytes(ruta)))
        pred = clasificador.predecir(x)
        resultados[ruta.name] = {
            "hipotesis": [{"clase": h.clase, "confianza": round(h.confianza, 6)} for h in pred.hipotesis]
        }
    SALIDA.write_text(json.dumps(resultados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(config.BASE_DIR)} con {len(resultados) - 2} ejemplos")


if __name__ == "__main__":
    main()
