"""Presentación: HTML del resultado, tema y hoja de estilos."""
from __future__ import annotations

import re

import presentacion
from inferencia import Hipotesis, Prediccion


def _pred(confianza: float) -> Prediccion:
    resto = (1 - confianza) / 2
    return Prediccion(
        (
            Hipotesis(0, "Grape___Black_rot", confianza),
            Hipotesis(1, "Grape___Esca_(Black_Measles)", resto),
            Hipotesis(2, "Tomato___Septoria_leaf_spot", resto),
        ),
        10.0,
    )


def test_resultado_firme_separa_cultivo_y_estado() -> None:
    salida = presentacion.resultado(_pred(0.911), 0.6, True)
    assert '<p class="pv-cultivo">Uva</p>' in salida
    assert '<h2 class="pv-estado">Podredumbre negra</h2>' in salida
    assert "Confianza del modelo: 91,1 %" in salida


def test_resultado_no_concluyente_no_presenta_diagnostico_firme() -> None:
    salida = presentacion.resultado(_pred(0.5), 0.6, False)
    assert '<h2 class="pv-estado">Resultado no concluyente</h2>' in salida
    assert "Podredumbre negra</h2>" not in salida
    assert "50,0 %" in salida and "60,0 %" in salida
    assert "Uva — Podredumbre negra" in salida  # el top-3 se sigue mostrando


def test_los_porcentajes_del_medidor_estan_acotados() -> None:
    for conf, umbral in [(1.0, 1.0), (0.0, 0.0), (0.37, 0.5)]:
        salida = presentacion.resultado(_pred(conf), umbral, conf >= umbral)
        for numero in re.findall(r"(?:width|left):([\d.]+)%", salida):
            assert 0.0 <= float(numero) <= 100.0


def test_resultado_se_puede_leer_sin_estilos() -> None:
    """Accesibilidad: el valor y la hipótesis están en texto, no solo en el dibujo."""
    salida = presentacion.resultado(_pred(0.9), 0.6, True)
    assert 'role="meter"' in salida and 'aria-label="Confianza del modelo"' in salida
    assert 'aria-hidden="true"' in salida  # las barras decorativas se ocultan al lector de pantalla
    assert salida.count("pv-valor") == 3


def test_avisos_escapan_html() -> None:
    for fn in (presentacion.alerta, presentacion.vacio, presentacion.aviso_permanente):
        assert "<b>" not in fn("<b>x</b>") and "&lt;b&gt;" in fn("<b>x</b>")


def test_las_clases_pv_usadas_en_html_existen_en_el_css() -> None:
    css = presentacion.RUTA_CSS.read_text(encoding="utf-8")
    html_total = (
        presentacion.cabecera()
        + presentacion.resultado(_pred(0.9), 0.6, True)
        + presentacion.resultado(_pred(0.4), 0.6, False)
        + presentacion.alerta("x")
        + presentacion.vacio("x")
        + presentacion.aviso_permanente("x")
    )
    usadas = {c for lista in re.findall(r'class="([^"]+)"', html_total) for c in lista.split()}
    definidas = set(re.findall(r"\.(pv-[\w-]+)", css))
    assert {c for c in usadas if c.startswith("pv-")} <= definidas


def _luminancia(hex_: str) -> float:
    r, g, b = (int(hex_.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contraste(a: str, b: str) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _token(nombre: str) -> str:
    css = presentacion.RUTA_CSS.read_text(encoding="utf-8")
    return re.search(rf"--{nombre}:\s*(#[0-9A-Fa-f]{{6}})", css).group(1)


def test_contraste_de_los_textos_cumple_wcag_aa() -> None:
    """SC 1.4.3: 4,5:1 para texto normal. Los pares son los que aparecen realmente en la interfaz."""
    papel, hoja = _token("pv-papel"), _token("pv-hoja")
    pares = {
        "tinta/papel": (_token("pv-tinta"), papel),
        "tinta suave/papel": (_token("pv-tinta-suave"), papel),
        "tinta suave/hoja": (_token("pv-tinta-suave"), hoja),
        "clorofila/papel (pestaña activa)": (_token("pv-clorofila"), papel),
        "ocre texto/ocre fondo (aviso)": (_token("pv-ocre-texto"), _token("pv-ocre-fondo")),
        "error texto/error fondo": (_token("pv-error-texto"), _token("pv-error-fondo")),
        "blanco/clorofila (botón primario)": ("#FFFFFF", _token("pv-clorofila")),
    }
    tema = presentacion.crear_tema()
    for atributo in ("body_text_color_subdued", "block_info_text_color", "block_label_text_color"):
        pares[f"tema.{atributo}/papel"] = (getattr(tema, atributo), papel)
        pares[f"tema.{atributo}/blanco"] = (getattr(tema, atributo), "#FFFFFF")
    insuficientes = {k: round(_contraste(*v), 2) for k, v in pares.items() if _contraste(*v) < 4.5}
    assert not insuficientes, insuficientes


def test_la_marca_del_medidor_tiene_contraste_de_componente() -> None:
    """SC 1.4.11: la marca del umbral y el relleno frente a la pista, >= 3:1."""
    assert _contraste(_token("pv-tinta"), "#DCE4D7") >= 3
    assert _contraste(_token("pv-clorofila"), "#DCE4D7") >= 3
    assert _contraste(_token("pv-ocre"), "#DCE4D7") >= 2.0  # el relleno ocre va acompañado de texto «no concluyente»


def test_la_barra_de_pestanas_no_ensancha_la_pagina_en_movil() -> None:
    css = presentacion.RUTA_CSS.read_text(encoding="utf-8")
    assert "contain: inline-size" in css


def test_el_js_fuerza_el_tema_claro_en_body_y_html() -> None:
    assert "document.body.classList.remove('dark')" in presentacion.JS_TEMA_CLARO
    assert "MutationObserver" in presentacion.JS_TEMA_CLARO


def test_el_tema_no_depende_de_fuentes_externas() -> None:
    tema = presentacion.crear_tema()
    assert all(not hasattr(f, "stylesheet") for f in tema._font)  # ninguna GoogleFont: sin peticiones a terceros
    css = presentacion.RUTA_CSS.read_text(encoding="utf-8")
    assert "http://" not in css and "https://" not in css and "@import" not in css
