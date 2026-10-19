"""Crea ``docs/img/social.png`` (1200 x 627, el tamaño que usa LinkedIn para la vista previa de un enlace).

Compone el título con la captura real de la aplicación (``docs/img/app-resultado.jpg``). Usa la fuente
Segoe UI de Windows si está disponible; si no, no genera nada y lo avisa.

    python scripts/generar_imagen_social.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
FUENTES = {
    "negrita": [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\seguisb.ttf"],
    "normal": [r"C:\Windows\Fonts\segoeui.ttf"],
}
PAPEL, TINTA, TINTA_SUAVE, CLOROFILA, LINEA = "#F2F5EE", "#1D2A22", "#42524A", "#2B6B47", "#D6DED1"
ANCHO, ALTO = 1200, 627


def _fuente(tipo: str, tam: int) -> ImageFont.FreeTypeFont | None:
    for ruta in FUENTES[tipo]:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    return None


def _ajustar(dibujo: ImageDraw.ImageDraw, texto: str, fuente, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if dibujo.textlength(prueba, font=fuente) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return [*lineas, actual]


def main() -> int:
    titulo, normal = _fuente("negrita", 56), _fuente("normal", 29)
    if titulo is None or normal is None:
        print("No se encontró Segoe UI: no se genera la imagen social.", file=sys.stderr)
        return 1
    lienzo = Image.new("RGB", (ANCHO, ALTO), PAPEL)
    d = ImageDraw.Draw(lienzo)

    captura = Image.open(DOCS / "img" / "app-resultado.jpg").convert("RGB")
    ancho_c = 600
    captura = captura.resize((ancho_c, round(captura.height * ancho_c / captura.width)), Image.LANCZOS)
    x_c, y_c = ANCHO - ancho_c - 56, (ALTO - captura.height) // 2
    d.rectangle((x_c - 1, y_c - 1, x_c + ancho_c, y_c + captura.height), outline=LINEA, width=2)
    lienzo.paste(captura, (x_c, y_c))

    x, y, ancho_t = 64, 150, x_c - 64 - 40
    d.rectangle((x, y - 34, x + 72, y - 28), fill=CLOROFILA)
    for linea in ("Diagnóstico", "de hojas con IA"):
        d.text((x, y), linea, font=titulo, fill=TINTA)
        y += 68
    y += 16
    for linea in _ajustar(d, "Sube la foto de una hoja y el modelo propone qué enfermedad podría tener.", normal, ancho_t):
        d.text((x, y), linea, font=normal, fill=TINTA_SUAVE)
        y += 42
    salida = DOCS / "img" / "social.png"
    lienzo.save(salida, optimize=True)
    print(f"Escrito {salida.relative_to(RAIZ)} ({ANCHO}x{ALTO})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
