"""Presentación: tema de Gradio y fragmentos HTML (cabecera, resultado, avisos).

El resultado se dibuja como una «etiqueta de muestra»: nombre del cultivo y del estado,
un medidor de la confianza del modelo con una marca en el umbral, y las tres hipótesis.
Los estilos están en ``estilos.css`` (clases ``pv-*``). Sin fuentes ni recursos externos.
"""
from __future__ import annotations

import html

import gradio as gr

import config
import etiquetas
from inferencia import Prediccion

RUTA_CSS = config.BASE_DIR / "estilos.css"

# Forzar el tema claro: la paleta está pensada solo para él.
JS_TEMA_CLARO = """() => {
  const forzarClaro = () => {
    document.body.classList.remove('dark');
    document.documentElement.classList.remove('dark');
  };
  forzarClaro();
  new MutationObserver(forzarClaro).observe(document.body, { attributes: true, attributeFilter: ['class'] });
}"""

_CLOROFILA = gr.themes.Color(
    name="clorofila",
    c50="#F1F6F2", c100="#DDEBE0", c200="#BBD6C2", c300="#8FBBA0", c400="#5E9B77", c500="#3C8160",
    c600="#2B6B47", c700="#235839", c800="#1D462E", c900="#173824", c950="#0E2416",
)
_PAPEL = gr.themes.Color(
    name="papel",
    c50="#F2F5EE", c100="#E8EDE4", c200="#D6DED1", c300="#BDC8B7", c400="#9AA996", c500="#76877A",
    c600="#586A5B", c700="#42524A", c800="#2D3B33", c900="#1D2A22", c950="#121B16",
)


def crear_tema() -> gr.themes.Base:
    return gr.themes.Base(
        primary_hue=_CLOROFILA,
        neutral_hue=_PAPEL,
        font=("Segoe UI", "system-ui", "-apple-system", "sans-serif"),  # del sistema: sin peticiones a terceros
        font_mono=("Consolas", "ui-monospace", "monospace"),
        radius_size=gr.themes.sizes.radius_sm,
        text_size=gr.themes.sizes.text_lg,  # texto base de 16 px (el predeterminado de Gradio es 14 px)
    ).set(
        body_background_fill="#F2F5EE",
        body_text_color="#1D2A22",
        # Textos secundarios de Gradio (ayudas, etiquetas, pie): >= 4,5:1 sobre el papel y sobre blanco (SC 1.4.3).
        body_text_color_subdued="#586A5B",
        block_info_text_color="#586A5B",
        block_label_text_color="#586A5B",
        block_title_text_color="#1D2A22",
        button_primary_background_fill="#2B6B47",
        button_primary_background_fill_hover="#235839",
        button_primary_text_color="#FFFFFF",
        block_background_fill="#F2F5EE",
        block_border_width="0px",
        block_shadow="none",
    )


def _pct(valor: float) -> str:
    return f"{valor * 100:.1f} %".replace(".", ",")


def _e(texto: str) -> str:
    return html.escape(texto, quote=True)


def cabecera() -> str:
    return """
<header class="pv-cabecera">
  <svg class="pv-marca" viewBox="0 0 48 48" width="44" height="44" aria-hidden="true" focusable="false">
    <path d="M40 6C21 6 8 16 8 30c0 3 .6 5.600 1.700 8L4 44l2.600 1.200 5.200-5.600C14.200 41 17 42 20 42c14 0 20-14 20-36z" fill="#2B6B47"/>
    <path d="M12 38C19 28 27 20 36 13" stroke="#F2F5EE" stroke-width="2.200" stroke-linecap="round" fill="none"/>
  </svg>
  <div>
    <h1 class="pv-titulo">Diagnóstico de hojas</h1>
    <p class="pv-subtitulo">Sube la foto de una hoja y el modelo propone qué enfermedad podría tener.</p>
  </div>
</header>
"""


def aviso_permanente(texto: str) -> str:
    return f'<p class="pv-aviso" role="note">{_e(texto)}</p>'


def vacio(texto: str) -> str:
    return f'<div class="pv-vacio"><p>{_e(texto)}</p></div>'


def alerta(texto: str) -> str:
    return f'<div class="pv-alerta" role="alert"><p>{_e(texto)}</p></div>'


def resultado(pred: Prediccion, umbral: float, concluyente: bool) -> str:
    """Etiqueta de resultado con medidor (marca en el umbral) y las tres hipótesis."""
    top = pred.top1
    clase_estado = "firme" if concluyente else "nc"
    if concluyente:
        titulo = (
            f'<p class="pv-cultivo">{_e(etiquetas.cultivo_es(top.clase))}</p>'
            f'<h2 class="pv-estado">{_e(etiquetas.estado_es(top.clase))}</h2>'
        )
        explicacion = ""
    else:
        titulo = (
            '<p class="pv-cultivo">Sin diagnóstico firme</p>'
            '<h2 class="pv-estado">Resultado no concluyente</h2>'
        )
        explicacion = (
            f'<p class="pv-explicacion">La confianza del modelo en la hipótesis principal '
            f"({_pct(top.confianza)}) queda por debajo del umbral ({_pct(umbral)}). "
            "No tomes esta salida como un diagnóstico firme: prueba con otra foto de una sola hoja, "
            "con buena luz y fondo liso.</p>"
        )
    medidor = (
        f'<div class="pv-medidor" role="meter" aria-label="Confianza del modelo" '
        f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{top.confianza * 100:.1f}">'
        '<div class="pv-pista">'
        f'<div class="pv-relleno" style="width:{top.confianza * 100:.1f}%"></div>'
        f'<div class="pv-umbral" style="left:{umbral * 100:.1f}%"></div>'
        "</div>"
        f'<p class="pv-medidor-texto"><strong>Confianza del modelo: {_pct(top.confianza)}</strong>'
        f'<span>La marca vertical indica el umbral ({_pct(umbral)}).</span></p>'
        "</div>"
    )
    filas = "".join(
        f'<li><span class="pv-nombre">{_e(etiquetas.nombre_legible(h.clase))}</span>'
        f'<span class="pv-barra" aria-hidden="true"><i style="width:{h.confianza * 100:.1f}%"></i></span>'
        f'<span class="pv-valor">{_pct(h.confianza)}</span></li>'
        for h in pred.hipotesis
    )
    return (
        f'<section class="pv-resultado pv-resultado--{clase_estado}" aria-live="polite">'
        f"{titulo}{explicacion}{medidor}"
        '<h3 class="pv-sub">Las tres hipótesis más probables</h3>'
        f'<ol class="pv-alternativas">{filas}</ol>'
        "</section>"
    )
