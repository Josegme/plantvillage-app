"""Genera dos carruseles de Instagram (imágenes 1080 x 1350, formato 4:5) y sus textos.

Salida en ``redes/instagram/``: ``post1-01.png`` ... ``post2-03.png`` y ``textos.md`` (descripciones y textos
alternativos). Las cifras se leen de ``modelo/metricas_test.json``. Las imágenes usan la fuente Segoe UI de Windows;
si no está disponible, el script lo avisa y no genera nada.

    python scripts/generar_posts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import contenido  # noqa: E402

SALIDA = RAIZ / "redes" / "instagram"
ANCHO, ALTO, MARGEN = 1080, 1350, 88
PAPEL, TINTA, SUAVE = "#F2F5EE", "#1D2A22", "#42524A"
CLOROFILA, CLARA, LINEA = "#2B6B47", "#5E9B77", "#D6DED1"
OCRE, OCRE_FONDO, OCRE_TEXTO = "#B7841B", "#F6EEDC", "#4A3A12"
REPO = "github.com/Josegme/plantvillage-app"
RUTAS_FUENTES = {
    "normal": r"C:\Windows\Fonts\segoeui.ttf",
    "semi": r"C:\Windows\Fonts\seguisb.ttf",
    "negrita": r"C:\Windows\Fonts\segoeuib.ttf",
}

# Instagram limita el texto alternativo a 100 caracteres.
ALT_TEXTOS = {
    "post1-01": "Captura de la app: hoja de tomate y resultado «Tizón temprano» con la confianza del modelo.",
    "post1-02": "Tres pasos: subir la foto de una hoja, ver tres hipótesis y leer la confianza del modelo.",
    "post1-03": "Límites: se entrenó con fotos de laboratorio y no sustituye a un profesional agrónomo.",
    "post2-01": "Pasos del entrenamiento: fotos etiquetadas, modelo previo, ajuste y prueba con fotos nuevas.",
    "post2-02": "Ideas para mejorar el proyecto: fotos del campo, más cultivos, traducciones y mejoras.",
    "post2-03": "Cuatro fotos de hojas y la dirección del código en GitHub: github.com/Josegme/plantvillage-app.",
}

class FuentesNoDisponibles(RuntimeError):
    pass


def _fuente(tipo: str, tam: int) -> ImageFont.FreeTypeFont:
    ruta = Path(RUTAS_FUENTES[tipo])
    if not ruta.exists():
        raise FuentesNoDisponibles(f"No se encontró la fuente {ruta}")
    return ImageFont.truetype(str(ruta), tam)


def _lineas(texto: str, fuente: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    salida: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if fuente.getlength(prueba) <= ancho:
                actual = prueba
            else:
                salida.append(actual)
                actual = palabra
        salida.append(actual)
    return salida


class Lienzo:
    def __init__(self, n: int, total: int) -> None:
        self.img = Image.new("RGB", (ANCHO, ALTO), PAPEL)
        self.d = ImageDraw.Draw(self.img)
        self.d.rectangle((MARGEN, 84, MARGEN + 84, 92), fill=CLOROFILA)  # barra de marca
        self.d.text((MARGEN, ALTO - 84), REPO, font=_fuente("normal", 30), fill=SUAVE, anchor="ls")
        self.d.text((ANCHO - MARGEN, ALTO - 84), f"{n}/{total}", font=_fuente("normal", 30), fill=SUAVE, anchor="rs")

    def texto(self, x: int, y: int, texto: str, fuente, color: str = TINTA, ancho: int | None = None,
              interlineado: float = 1.28) -> int:
        """Dibuja texto con ajuste de línea y devuelve la y siguiente."""
        ancho = ancho if ancho is not None else ANCHO - MARGEN - x
        paso = round(fuente.size * interlineado)
        for linea in _lineas(texto, fuente, ancho):
            self.d.text((x, y), linea, font=fuente, fill=color, anchor="la")
            y += paso
        return y

    def paso(self, y: int, numero: int, texto: str, tam: int = 54) -> int:
        """Fila numerada: círculo verde con el número y el texto al lado. Devuelve la y siguiente."""
        r = 42
        self.d.ellipse((MARGEN, y, MARGEN + 2 * r, y + 2 * r), fill=CLOROFILA)
        self.d.text((MARGEN + r, y + r), str(numero), font=_fuente("negrita", 46), fill="#FFFFFF", anchor="mm")
        x = MARGEN + 2 * r + 32
        fin = self.texto(x, y - 8, texto, _fuente("normal", tam), TINTA, ANCHO - MARGEN - x, 1.3)
        return max(fin, y + 2 * r) + 52

    def vineta(self, y: int, texto: str, tam: int = 54, color: str = TINTA) -> int:
        self.d.rectangle((MARGEN, y + 18, MARGEN + 18, y + 36), fill=CLOROFILA)
        x = MARGEN + 18 + 30
        return self.texto(x, y - 8, texto, _fuente("normal", tam), color, ANCHO - MARGEN - x, 1.3) + 40

    def foto(self, ruta: Path, x: int, y: int, ancho: int) -> int:
        with Image.open(ruta) as im:
            im = im.convert("RGB")
            alto = round(im.height * ancho / im.width)
            im = im.resize((ancho, alto), Image.LANCZOS)
        self.d.rectangle((x - 2, y - 2, x + ancho + 1, y + alto + 1), outline=LINEA, width=2)
        self.img.paste(im, (x, y))
        return y + alto

    def guardar(self, nombre: str) -> Path:
        SALIDA.mkdir(parents=True, exist_ok=True)
        ruta = SALIDA / f"{nombre}.png"
        self.img.save(ruta, optimize=True)
        return ruta


def _fila_fotos(s: Lienzo, y: int, claves: tuple[str, ...] = ("Grape", "Tomato_Early", "Corn", "Strawberry")) -> None:
    ejemplos = sorted((RAIZ / "docs" / "img" / "ejemplos").glob("*.jpg"))
    elegidos = [next(e for e in ejemplos if k in e.name) for k in claves]
    lado = 200
    hueco = (ANCHO - 2 * MARGEN - lado * len(elegidos)) // (len(elegidos) - 1)
    for i, foto in enumerate(elegidos):
        s.foto(foto, MARGEN + i * (lado + hueco), y, lado)


def _caja_aviso(s: Lienzo, y: int, texto: str, tam: int = 42) -> int:
    fuente = _fuente("semi", tam)
    lineas = _lineas(texto, fuente, ANCHO - 2 * MARGEN - 80)
    alto = round(len(lineas) * tam * 1.25) + 64
    s.d.rectangle((MARGEN, y, ANCHO - MARGEN, y + alto), fill=OCRE_FONDO)
    s.d.rectangle((MARGEN, y, MARGEN + 8, y + alto), fill=OCRE)
    s.texto(MARGEN + 40, y + 32, texto, fuente, OCRE_TEXTO, ANCHO - 2 * MARGEN - 80, 1.25)
    return y + alto


def _post1(v: dict[str, str]) -> list[Path]:
    titulo = _fuente("negrita", 84)
    rutas = []

    s = Lienzo(1, 3)
    y = s.texto(MARGEN, 150, "Una IA que mira una hoja y propone qué enfermedad podría tener", _fuente("negrita", 72), interlineado=1.15)
    s.foto(RAIZ / "docs" / "img" / "app-resultado.jpg", MARGEN, y + 50, ANCHO - 2 * MARGEN)
    rutas.append(s.guardar("post1-01"))

    s = Lienzo(2, 3)
    y = s.texto(MARGEN, 150, "Cómo funciona", titulo, interlineado=1.15) + 60
    y = s.paso(y, 1, "Subes la foto de una hoja o usas la cámara.")
    y = s.paso(y, 2, "El modelo propone las 3 enfermedades más parecidas.")
    y = s.paso(y, 3, "Te dice cuánta confianza tiene. Si no está seguro, lo dice: «resultado no concluyente».")
    s.texto(MARGEN, y + 30, "Reconoce 38 casos de 14 cultivos: tomate, papa, maíz, uva, manzana, fresa…", _fuente("semi", 44), CLOROFILA)
    rutas.append(s.guardar("post1-02"))

    s = Lienzo(3, 3)
    y = s.texto(MARGEN, 150, "Honesta con sus límites", titulo, interlineado=1.15) + 60
    y = s.vineta(y, f"Acertó el {v['exactitud_test']} de las hojas de prueba, fotos que nunca había visto.", 50)
    y = s.vineta(y, "Se entrenó con fotos de laboratorio: con fotos del campo rinde peor.", 50)
    y = s.vineta(y, "No sabe decir «esto no es una hoja».", 50) + 10
    _caja_aviso(s, y + 20, "Es una demostración. No sustituye el diagnóstico de un profesional agrónomo.")
    rutas.append(s.guardar("post1-03"))
    return rutas


def _post2() -> list[Path]:
    titulo = _fuente("negrita", 84)
    rutas = []

    s = Lienzo(1, 3)
    y = s.texto(MARGEN, 150, "Así se entrenó", titulo, interlineado=1.15) + 50
    for n, paso in enumerate((
        "Más de 54.000 fotos de hojas ya etiquetadas.",
        "Partir de un modelo que ya sabe mirar imágenes.",
        "Ajustarlo con cuidado para que aprenda hojas.",
        "Probarlo con fotos que nunca vio.",
    ), start=1):
        y = s.paso(y, n, paso, 50)
    s.texto(MARGEN, y - 6, "El porqué de cada paso está en la página del proyecto.", _fuente("semi", 42), CLOROFILA)
    rutas.append(s.guardar("post2-01"))

    s = Lienzo(2, 3)
    y = s.texto(MARGEN, 150, "Hecha para mejorarse", titulo, interlineado=1.15) + 20
    y = s.texto(MARGEN, y, "Algunas ideas si quieres ayudar:", _fuente("normal", 48), SUAVE) + 40
    for idea in (
        "Probarla con fotos tomadas en el campo.",
        "Añadir más cultivos y enfermedades.",
        "Traducirla a otros idiomas.",
        "Mejorar el modelo o la interfaz.",
        "Revisar los textos y avisar de errores.",
    ):
        y = s.vineta(y, idea)
    rutas.append(s.guardar("post2-02"))

    s = Lienzo(3, 3)
    y = s.texto(MARGEN, 150, "El código es público", titulo, interlineado=1.15) + 20
    y = s.texto(MARGEN, y, "Está en GitHub. Si quieres mejorarlo, abre un issue o un pull request.", _fuente("normal", 50), TINTA) + 40
    y = s.texto(MARGEN, y, REPO, _fuente("negrita", 46), CLOROFILA, interlineado=1.2)
    s.texto(MARGEN, y + 8, "Enlace en la bio.", _fuente("semi", 46), SUAVE)
    _fila_fotos(s, 800)
    rutas.append(s.guardar("post2-03"))
    return rutas

def _textos(v: dict[str, str]) -> str:
    hashtags1 = "#inteligenciaartificial #machinelearning #python #agricultura #tensorflow #gradio #proyectopersonal #portafolio"
    hashtags2 = "#inteligenciaartificial #aprendizajeautomatico #python #github #colaboracion #aprendizaje #proyectopersonal #agricultura"
    post1 = f"""🌿 Hice una app que mira la foto de una hoja y propone qué enfermedad podría tener.

La subes (o la sacas con la cámara), el modelo te da sus 3 hipótesis y te dice cuánta confianza tiene. Si no está seguro, no inventa: avisa con un «resultado no concluyente».

Reconoce 38 casos de 14 cultivos (tomate, papa, maíz, uva, manzana, fresa…). En las {v['n_test']} fotos de prueba que nunca había visto, acertó el {v['exactitud_test']}.

⚠️ Es una demostración: se entrenó con fotos de laboratorio y no sustituye a un profesional agrónomo.

📖 La explicación completa, paso a paso y pensada para quien no sabe nada de IA, está en la página del proyecto. Enlace en mi bio 👆

{hashtags1}"""
    post2 = f"""🧠 ¿Cómo se entrena una IA para reconocer enfermedades en hojas? En 4 pasos:

1️⃣ Más de 54.000 fotos ya etiquetadas (PlantVillage)
2️⃣ Partir de un modelo que ya sabe mirar imágenes (MobileNetV2)
3️⃣ Ajustarlo con cuidado para que aprenda a reconocer hojas
4️⃣ Probarlo con fotos que nunca vio

💡 El código es público en GitHub y me encantaría que lo mejoraran: probarlo con fotos del campo, sumar cultivos, traducirlo o mejorar el modelo. Abre un issue o un pull request.

👉 El enlace al repositorio está en mi bio.

{hashtags2}"""
    alts = "\n".join(f"- `{k}`: {t}" for k, t in ALT_TEXTOS.items())
    return f"""# Textos para Instagram

Generado por `scripts/generar_posts.py`. Las imágenes están en esta misma carpeta (1080 × 1350 px, formato 4:5).
Instagram no convierte en enlace lo que pongas en la descripción: usa el enlace de la bio.

## Publicación 1 · Presentación (carrusel de 3 imágenes: `post1-01` a `post1-03`)

{post1}

## Publicación 2 · Cómo se hizo y cómo mejorarlo (carrusel de 3 imágenes: `post2-01` a `post2-03`)

{post2}

## Textos alternativos (accesibilidad)

En Instagram: al subir cada imagen, «Accesibilidad» → «Escribir texto alternativo».

{alts}

## Enlace de la bio

Sugerencias: la página del proyecto (https://josegme.github.io/plantvillage-app/), que lleva al repositorio, o directamente https://github.com/Josegme/plantvillage-app.
"""


def generar() -> list[Path]:
    v = contenido.valores()
    rutas = [*_post1(v), *_post2()]
    texto = SALIDA / "textos.md"
    texto.write_text(_textos(v), encoding="utf-8")
    return [*rutas, texto]


if __name__ == "__main__":
    try:
        for r in generar():
            print(f"Escrito {r.relative_to(RAIZ)}")
    except FuentesNoDisponibles as e:
        print(f"{e}: no se generan las imágenes.", file=sys.stderr)
        raise SystemExit(1)
