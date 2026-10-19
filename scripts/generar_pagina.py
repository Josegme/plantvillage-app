"""Genera la página de proyecto (``docs/index.html``) para GitHub Pages.

Es una página estática: no ejecuta el modelo. Reutiliza los textos de ``contenido/*.md`` (con las cifras
leídas de ``modelo/``), las predicciones reales de ``contenido/ejemplos_demo.json`` y el mismo
componente de resultado que usa la aplicación (``presentacion.resultado``).

    python scripts/generar_pagina.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from markdown_it import MarkdownIt  # noqa: E402
from PIL import Image  # noqa: E402

import config  # noqa: E402
import contenido  # noqa: E402
import etiquetas  # noqa: E402
import metricas  # noqa: E402
import presentacion  # noqa: E402
from inferencia import Hipotesis, Prediccion  # noqa: E402

DOCS = RAIZ / "docs"
URL_PAGINA = "https://josegme.github.io/plantvillage-app/"
UMBRALES = (0.60, 0.95)  # el segundo muestra cómo cambia un resultado al subir el umbral
TITULO = "Diagnóstico de hojas con inteligencia artificial"
DESCRIPCION = (
    "Aplicación que mira la foto de una hoja y propone qué enfermedad podría tener. "
    "Explicación para quien no conoce el tema y recorrido paso a paso de cómo se entrenó el modelo."
)

_md = MarkdownIt("commonmark").enable("table")
_e = html.escape


def _md_html(nombre: str) -> str:
    return _md.render(contenido.cargar(nombre))


def _clase_real(nombre_archivo: str) -> str:
    """Clase real de un ejemplo: el nombre del archivo es la clase con los símbolos cambiados por «_»."""
    stem = Path(nombre_archivo).stem
    for clase in json.loads(config.RUTA_CLASES.read_text(encoding="utf-8")):
        if re.sub(r"[^A-Za-z0-9]+", "_", clase).strip("_") == stem:
            return clase
    raise KeyError(f"El ejemplo {nombre_archivo!r} no corresponde a ninguna clase")


def _ejemplos() -> list[dict]:
    datos = json.loads((config.BASE_DIR / "contenido" / "ejemplos_demo.json").read_text(encoding="utf-8"))
    salida = []
    for nombre, valor in datos.items():
        if nombre.startswith("_"):
            continue
        hip = tuple(Hipotesis(i, h["clase"], h["confianza"]) for i, h in enumerate(valor["hipotesis"]))
        salida.append({"archivo": nombre, "real": _clase_real(nombre), "pred": Prediccion(hip, 0.0)})
    return salida


def _galeria() -> str:
    ejemplos = _ejemplos()
    miniaturas = "".join(
        f'<button type="button" class="miniatura" data-ejemplo="{i}" aria-pressed="{"true" if i == 0 else "false"}" '
        f'aria-label="{_e(etiquetas.nombre_legible(e["real"]))}">'
        f'<img src="img/ejemplos/{_e(e["archivo"])}" alt="" width="72" height="72" loading="lazy"></button>'
        for i, e in enumerate(ejemplos)
    )
    umbrales = "".join(
        f'<label><input type="radio" name="umbral" value="{round(u * 100)}"{" checked" if k == 0 else ""}> '
        f'{round(u * 100)} %{" (valor por defecto)" if k == 0 else ""}</label>'
        for k, u in enumerate(UMBRALES)
    )
    muestras = []
    for i, e in enumerate(ejemplos):
        for k, u in enumerate(UMBRALES):
            concluyente = e["pred"].top1.confianza >= u
            oculto = "" if (i == 0 and k == 0) else " hidden"
            muestras.append(
                f'<article class="muestra" data-ejemplo="{i}" data-umbral="{round(u * 100)}"{oculto}>'
                f'<figure><img src="img/ejemplos/{_e(e["archivo"])}" '
                f'alt="Foto de ejemplo: {_e(etiquetas.nombre_legible(e["real"]))}" width="256" height="256">'
                f'<figcaption>Clase real del ejemplo: {_e(etiquetas.nombre_legible(e["real"]))}</figcaption></figure>'
                f"{presentacion.resultado(e['pred'], u, concluyente)}"
                "</article>"
            )
    return (
        '<div class="galeria">'
        '<div class="controles">'
        f'<div class="miniaturas" role="group" aria-label="Foto de ejemplo">{miniaturas}</div>'
        f'<fieldset class="umbral"><legend>Umbral de confianza</legend>{umbrales}</fieldset>'
        "</div>"
        f'<div class="muestras">{"".join(muestras)}</div>'
        "</div>"
    )


JS_GALERIA = """
(function () {
  var galeria = document.querySelector('.galeria');
  if (!galeria) return;
  var muestras = galeria.querySelectorAll('.muestra');
  var botones = galeria.querySelectorAll('.miniatura');
  var ejemplo = '0';
  function umbral() { return galeria.querySelector('input[name="umbral"]:checked').value; }
  function mostrar() {
    var u = umbral();
    muestras.forEach(function (m) { m.hidden = !(m.dataset.ejemplo === ejemplo && m.dataset.umbral === u); });
    botones.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.ejemplo === ejemplo)); });
  }
  botones.forEach(function (b) { b.addEventListener('click', function () { ejemplo = b.dataset.ejemplo; mostrar(); }); });
  galeria.querySelectorAll('input[name="umbral"]').forEach(function (r) { r.addEventListener('change', mostrar); });
})();
"""


def _video() -> str:
    if not (DOCS / "demo.mp4").exists():
        return ""
    poster = ' poster="img/app-resultado.jpg"' if (DOCS / "img" / "app-resultado.jpg").exists() else ""
    return (
        '<section id="video" aria-labelledby="t-video"><h2 id="t-video">La aplicación en funcionamiento</h2>'
        f'<video controls preload="metadata" width="960"{poster}><source src="demo.mp4" type="video/mp4">'
        "Tu navegador no puede reproducir este vídeo.</video></section>"
    )


def _pagina() -> str:
    v = contenido.valores()
    m = metricas.cargar_metricas()
    with Image.open(DOCS / "img" / "app-resultado.jpg") as captura:
        _ANCHO_CAPTURA, _ALTO_CAPTURA = captura.size
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(TITULO)} · PlantVillage</title>
<meta name="description" content="{_e(DESCRIPCION)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{_e(TITULO)}">
<meta property="og:description" content="{_e(DESCRIPCION)}">
<meta property="og:url" content="{URL_PAGINA}">
<meta property="og:image" content="{URL_PAGINA}img/social.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="627">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="app-estilos.css">
<link rel="stylesheet" href="pagina.css">
<noscript><style>.muestra[data-umbral="60"][hidden]{{display:grid}}.controles{{display:none}}</style></noscript>
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<header class="sitio">
  <nav aria-label="Secciones de la página">
    <a href="#probar">Ejemplos</a>
    <a href="#para-que-sirve">Para qué sirve</a>
    <a href="#como-se-hizo">Cómo se hizo</a>
    <a href="#ejecutarlo">Ejecutarlo</a>
    <a href="#creditos">Créditos</a>
  </nav>
</header>
<main id="contenido">
  <section class="portada" aria-labelledby="t-portada">
    <div class="portada-texto">
      <h1 id="t-portada">Diagnóstico de hojas con inteligencia artificial</h1>
      <p class="entradilla">Sube la foto de una hoja y la aplicación propone qué enfermedad podría tener.
      Reconoce {m["n_clases"]} clases de 14 cultivos y acierta el {v["exactitud_test"]} de las hojas de prueba.</p>
      <p class="acciones">
        <a class="boton" href="{config.REPOSITORIO_URL}">Ver el código en GitHub</a>
        <a class="enlace" href="#como-se-hizo">Cómo se hizo, paso a paso</a>
      </p>
      <p class="nota-aviso" role="note">Herramienta demostrativa: no sustituye el diagnóstico de un profesional agronómico.</p>
    </div>
    <figure class="portada-captura">
      <img src="img/app-resultado.jpg" width="{_ANCHO_CAPTURA}" height="{_ALTO_CAPTURA}"
           alt="Captura de la aplicación: foto de una hoja de tomate a la izquierda y, a la derecha, el resultado «Tizón temprano» con la confianza del modelo y las tres hipótesis.">
      <figcaption>La aplicación funcionando en un ordenador.</figcaption>
    </figure>
  </section>

  <section id="probar" aria-labelledby="t-probar">
    <h2 id="t-probar">Prueba con una hoja de ejemplo</h2>
    <p class="intro">Estos son los resultados reales del modelo para las ocho fotos de ejemplo. No es una demostración en
    vivo: la aplicación calcula cada resultado en el momento. Cambia el umbral para ver cómo un resultado seguro deja de
    serlo cuando se exige más confianza.</p>
    {_galeria()}
  </section>

  <section id="para-que-sirve" class="lectura">
    {_md_html("para_que_sirve")}
  </section>

  <section id="como-se-hizo" class="lectura">
    {_md_html("como_se_hizo")}
  </section>

  {_video()}

  <section id="ejecutarlo" class="lectura" aria-labelledby="t-ejecutarlo">
    <h2 id="t-ejecutarlo">Ejecutarlo en tu equipo</h2>
    <p>Necesitas Python 3.13 y <a href="https://git-lfs.com">Git LFS</a> (el modelo se guarda con esa extensión de Git).
    En Windows, desde PowerShell:</p>
    <pre><code>git clone {config.REPOSITORIO_URL}.git
cd plantvillage-app
py -3.13 -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe app.py</code></pre>
    <p>Después abre <code>http://127.0.0.1:7860</code> en el navegador. En macOS o Linux, usa <code>python3.13</code> y
    <code>.venv/bin/python</code>. La pestaña de administración solo se activa si defines antes la variable de entorno
    <code>ADMIN_PASSWORD</code>.</p>
  </section>

  <section id="creditos" class="lectura" aria-labelledby="t-creditos">
    <h2 id="t-creditos">Créditos y límites</h2>
    <p>El modelo se entrenó con <strong>PlantVillage</strong> (Hughes y Salathé, 2015,
    <a href="https://arxiv.org/abs/1511.08060">An open access repository of images on plant health to enable the
    development of mobile disease diagnostics</a>). El mérito del conjunto de datos es de sus autores.</p>
    <p>Es un proyecto de aprendizaje. Se entrenó con fotos de laboratorio y puede fallar con fotos del campo o con
    imágenes que no sean hojas. La confianza que muestra no es una medida exacta de acierto.</p>
  </section>
</main>
<footer class="pie">
  <p>Código fuente y documentación en <a href="{config.REPOSITORIO_URL}">GitHub</a>.</p>
</footer>
<script>{JS_GALERIA}</script>
</body>
</html>
"""


def generar(destino: Path = DOCS) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RAIZ / "estilos.css", destino / "app-estilos.css")
    salida = destino / "index.html"
    salida.write_text(_pagina(), encoding="utf-8")
    return salida


if __name__ == "__main__":
    print(f"Escrito {generar().relative_to(RAIZ)}")
