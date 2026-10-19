"""Imágenes y textos para Instagram (scripts/generar_posts.py)."""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

import config

sys.path.insert(0, str(config.BASE_DIR / "scripts"))
generar_posts = importlib.import_module("generar_posts")

pytestmark = pytest.mark.skipif(
    not all(Path(r).exists() for r in generar_posts.RUTAS_FUENTES.values()),
    reason="requiere las fuentes Segoe UI de Windows",
)


@pytest.fixture(scope="module")
def salida(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destino = tmp_path_factory.mktemp("redes")
    original = generar_posts.SALIDA
    generar_posts.SALIDA = destino
    try:
        generar_posts.generar()
    finally:
        generar_posts.SALIDA = original
    return destino


def test_seis_imagenes_en_formato_4_5(salida: Path) -> None:
    nombres = [f"post{p}-0{i}.png" for p in (1, 2) for i in (1, 2, 3)]
    assert sorted(x.name for x in salida.glob("*.png")) == nombres
    for n in nombres:
        with Image.open(salida / n) as im:
            assert im.size == (1080, 1350), n


def test_el_texto_no_invade_el_pie_de_pagina(salida: Path) -> None:
    """Zona del pie (y > 1200) sin tinta salvo la propia línea del pie, que empieza en y = 1236."""
    for ruta in salida.glob("*.png"):
        with Image.open(ruta).convert("RGB") as im:
            franja = im.crop((0, 1196, 1080, 1230))
            colores = {c for _, c in franja.getcolors(maxcolors=100000)}
            assert colores == {(242, 245, 238)}, f"{ruta.name}: contenido en la franja previa al pie"


def _secciones(texto: str) -> dict[str, str]:
    partes = re.split(r"^## ", texto, flags=re.M)[1:]
    return {p.split("\n", 1)[0]: p.split("\n", 1)[1] for p in partes}


def test_descripciones_cumplen_los_limites_de_instagram(salida: Path) -> None:
    secciones = _secciones((salida / "textos.md").read_text(encoding="utf-8"))
    pubs = [v for k, v in secciones.items() if k.startswith("Publicación")]
    assert len(pubs) == 2
    for pub in pubs:
        assert len(pub) <= 2200
        assert len(re.findall(r"#\w+", pub)) <= 10
        assert "bio" in pub.lower()
        assert "http" not in pub  # los enlaces de la descripción no son clicables en Instagram
        assert not re.search("probabilidad", pub, re.IGNORECASE)


def test_las_cifras_de_las_descripciones_salen_de_los_archivos(salida: Path) -> None:
    import contenido

    v = contenido.valores()
    texto = (salida / "textos.md").read_text(encoding="utf-8")
    assert v["exactitud_test"] in texto and v["n_test"] in texto
    assert "{{" not in texto


def test_textos_alternativos_de_100_caracteres_como_maximo() -> None:
    assert set(generar_posts.ALT_TEXTOS) == {f"post{p}-0{i}" for p in (1, 2) for i in (1, 2, 3)}
    for clave, alt in generar_posts.ALT_TEXTOS.items():
        assert 20 < len(alt) <= 100, (clave, len(alt))


def test_las_imagenes_de_redes_no_se_suben_al_repositorio() -> None:
    assert "redes/instagram/*.png" in (config.BASE_DIR / ".gitignore").read_text(encoding="utf-8")
