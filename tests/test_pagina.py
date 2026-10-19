"""Página de proyecto (docs/): contenido, enlaces, accesibilidad básica y coherencia con los datos."""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

import config

sys.path.insert(0, str(config.BASE_DIR / "scripts"))
generar_pagina = importlib.import_module("generar_pagina")

DOCS = config.BASE_DIR / "docs"
HOSTS_PERMITIDOS = ("github.com/Josegme", "git-lfs.com", "arxiv.org", "josegme.github.io")


@pytest.fixture(scope="module")
def pagina(tmp_path_factory: pytest.TempPathFactory) -> str:
    destino = tmp_path_factory.mktemp("docs")
    return generar_pagina.generar(destino).read_text(encoding="utf-8")


def _texto(fragmento: str) -> str:
    import html

    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", "", fragmento, flags=re.S)))


def test_la_pagina_commiteada_esta_al_dia(pagina: str) -> None:
    """docs/index.html debe ser exactamente lo que genera el script (si no, hay que volver a ejecutarlo)."""
    assert (DOCS / "index.html").read_text(encoding="utf-8") == pagina


def test_estructura_basica(pagina: str) -> None:
    assert pagina.startswith("<!doctype html>") and '<html lang="es">' in pagina
    assert len(re.findall(r"<h1[ >]", pagina)) == 1
    assert re.search(r"<title>[^<]{10,}</title>", pagina)
    assert 'name="description"' in pagina and 'name="viewport"' in pagina
    assert 'class="saltar"' in pagina  # enlace «Saltar al contenido»
    assert "{{" not in pagina and "}}" not in re.sub(r"<script>.*?</script>|<style>.*?</style>|<noscript>.*?</noscript>", "", pagina, flags=re.S)


def test_las_cifras_salen_de_los_archivos_del_modelo(pagina: str) -> None:
    import contenido

    v = contenido.valores()
    texto = _texto(pagina)
    for clave in ("exactitud_test", "f1_macro_test", "top3_test", "n_test"):
        assert v[clave] in texto, clave


def test_las_referencias_locales_existen(pagina: str) -> None:
    refs = re.findall(r'(?:src|href)="([^"]+)"', pagina)
    locales = [r for r in refs if not r.startswith(("http", "#", "mailto:"))]
    assert locales
    faltan = [r for r in locales if not (DOCS / r).exists()]
    assert not faltan, faltan


def test_sin_recursos_externos_y_enlaces_solo_a_sitios_esperados(pagina: str) -> None:
    sin_og = re.sub(r'<meta[^>]+>', "", pagina)
    assert not re.search(r'<(?:script|img|link|video|source)[^>]+(?:src|href)="https?://', sin_og)
    for url in re.findall(r'href="(https?://[^"]+)"', sin_og):
        assert any(h in url for h in HOSTS_PERMITIDOS), url


def test_todas_las_imagenes_tienen_alt(pagina: str) -> None:
    imgs = re.findall(r"<img\b[^>]*>", pagina)
    assert len(imgs) >= 17  # captura + 8 miniaturas + 16 fotos de muestra (algunas ocultas) en total
    assert all(re.search(r"\balt=", i) for i in imgs)
    con_texto = [i for i in imgs if 'alt=""' not in i]
    assert all(len(re.search(r'alt="([^"]*)"', i).group(1)) > 10 for i in con_texto)


def test_imagen_para_redes_sociales(pagina: str) -> None:
    assert f'<meta property="og:image" content="{generar_pagina.URL_PAGINA}img/social.png">' in pagina
    with Image.open(DOCS / "img" / "social.png") as im:
        assert im.size == (1200, 627)
    assert (DOCS / ".nojekyll").exists()


def test_la_galeria_tiene_8_ejemplos_x_2_umbrales_y_una_sola_visible(pagina: str) -> None:
    muestras = re.findall(r'<article class="muestra"[^>]*>', pagina)
    assert len(muestras) == 16
    assert sum(1 for m in muestras if " hidden" not in m) == 1


def test_el_umbral_alto_vuelve_no_concluyente_un_resultado_seguro(pagina: str) -> None:
    grape = next(e for e in generar_pagina._ejemplos() if e["archivo"] == "Grape_Black_rot.jpg")
    assert 0.60 <= grape["pred"].top1.confianza < 0.95
    firme = re.search(r'<article class="muestra"[^>]*data-umbral="60"[^>]*>(?:(?!</article>).)*Grape_Black_rot(?:(?!</article>).)*</article>', pagina, re.S)
    nc = re.search(r'<article class="muestra"[^>]*data-umbral="95"[^>]*>(?:(?!</article>).)*Grape_Black_rot(?:(?!</article>).)*</article>', pagina, re.S)
    assert firme and "pv-resultado--firme" in firme.group(0)
    assert nc and "pv-resultado--nc" in nc.group(0) and "Resultado no concluyente" in nc.group(0)


def test_las_clases_reales_de_los_ejemplos_coinciden_con_la_prediccion() -> None:
    """Los ocho ejemplos se eligieron entre los bien clasificados: top-1 == clase real."""
    for e in generar_pagina._ejemplos():
        assert e["pred"].top1.clase == e["real"], e["archivo"]


def test_ejemplos_demo_coinciden_con_la_instantanea_del_modelo() -> None:
    """Si cambian el modelo o el preprocesado, hay que volver a ejecutar scripts/generar_ejemplos.py."""
    demo = json.loads((config.BASE_DIR / "contenido" / "ejemplos_demo.json").read_text(encoding="utf-8"))
    instantanea = json.loads((config.BASE_DIR / "tests" / "instantanea_local.json").read_text(encoding="utf-8"))
    for nombre, valor in demo.items():
        if nombre.startswith("_"):
            continue
        for h, esperado in zip(valor["hipotesis"], instantanea[nombre]):
            assert h["clase"] == esperado["clase"]
            assert h["confianza"] == pytest.approx(esperado["confianza"], abs=1e-4)


def test_nunca_aparece_la_palabra_probabilidad(pagina: str) -> None:
    assert not re.search("probabilidad", _texto(pagina), re.IGNORECASE)


def test_el_video_solo_aparece_si_existe_el_archivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generar_pagina, "DOCS", tmp_path)
    assert generar_pagina._video() == ""
    (tmp_path / "demo.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    assert "<video" in generar_pagina._video()


def test_las_secciones_del_menu_existen(pagina: str) -> None:
    anclas = re.findall(r'<a href="#([\w-]+)">', pagina)
    ids = set(re.findall(r'\bid="([\w-]+)"', pagina))
    assert anclas and set(anclas) <= ids, set(anclas) - ids
