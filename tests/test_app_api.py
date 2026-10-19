"""(e, vía API) La autorización de administración se aplica también por la ruta HTTP/API.

``api_name=False`` solo oculta los eventos de la documentación de la API; Gradio sigue
aceptando ``fn_index`` en ``/queue/join``. Por eso estos tests llaman a las funciones de
administración por esa vía HTTP directa y comprueban que sin sesión válida NO devuelven datos.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import gradio as gr
import httpx
import pytest

import app
from admin import Administracion
from historial import Historial

PASSWORD = "clave-solo-para-tests"
MARCA = "CLASE_SECRETA_TEST"  # texto sembrado en el historial que nunca debe filtrarse sin sesión


class Cliente:
    def __init__(self, base: str, demo: gr.Blocks) -> None:
        self.base = base.rstrip("/")
        self.demo = demo
        self.sesion = uuid.uuid4().hex

    def _fn_id(self, nombre: str) -> int:
        ids = [i for i, f in self.demo.fns.items() if getattr(f, "name", None) == nombre]
        assert ids, f"función {nombre!r} no encontrada"
        return min(ids)  # "entrar" está enlazada a dos eventos (botón y Enter) con la misma función

    def llamar(self, nombre: str, datos: list) -> dict:
        cuerpo = {"data": datos, "fn_index": self._fn_id(nombre), "session_hash": self.sesion}
        r = httpx.post(f"{self.base}/gradio_api/queue/join", json=cuerpo, timeout=30)
        assert r.status_code == 200, r.text
        with httpx.stream(
            "GET", f"{self.base}/gradio_api/queue/data", params={"session_hash": self.sesion}, timeout=60
        ) as flujo:
            for linea in flujo.iter_lines():
                if not linea.startswith("data:"):
                    continue
                msg = json.loads(linea[5:])
                if msg.get("msg") == "process_completed":
                    return msg
        raise AssertionError("no hubo process_completed")

    def nueva_sesion(self) -> "Cliente":
        return Cliente(self.base, self.demo)


@pytest.fixture(scope="module")
def servidor(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[gr.Blocks, str]]:
    tmp = tmp_path_factory.mktemp("api")
    repo = Historial(tmp / "h.db")
    repo.registrar(MARCA, 0.9, False, 1.0, "0123456789abcdef")
    demo = app.construir_demo(None, repo, Administracion(password=PASSWORD))
    _, url, _ = demo.launch(prevent_thread_lock=True, quiet=True, server_port=None)
    try:
        yield demo, url
    finally:
        demo.close()


def _texto(msg: dict) -> str:
    return json.dumps(msg, ensure_ascii=False)


def test_eventos_de_admin_no_estan_en_la_documentacion_de_la_api(servidor: tuple[gr.Blocks, str]) -> None:
    demo, url = servidor
    info = httpx.get(f"{url.rstrip('/')}/gradio_api/info", timeout=30).json()
    endpoints = set(info["named_endpoints"]) | set(info["unnamed_endpoints"])
    assert "/diagnosticar" in endpoints
    assert not any(n in e for e in endpoints for n in ("entrar", "actualizar", "exportar", "salir"))


def test_sin_login_la_funcion_de_datos_no_devuelve_nada(servidor: tuple[gr.Blocks, str]) -> None:
    demo, url = servidor
    c = Cliente(url, demo)
    # Estado de sesión vacío; el cliente no puede forzar un token: los State los pone el servidor.
    for nombre, datos in [("actualizar", [None, "", False]), ("exportar", [None, "", False])]:
        msg = c.llamar(nombre, datos)
        assert MARCA not in _texto(msg), nombre
        assert "headers" not in _texto(msg) or "recall" not in _texto(msg)  # tampoco métricas por clase
    # Un token inventado en el cuerpo no se acepta: el State viaja por la sesión del servidor.
    msg = c.llamar("actualizar", ["token-inventado-por-el-atacante", "", False])
    assert MARCA not in _texto(msg)


def test_login_incorrecto_no_abre_nada(servidor: tuple[gr.Blocks, str]) -> None:
    demo, url = servidor
    c = Cliente(url, demo)
    msg = c.llamar("entrar", ["clave-equivocada"])
    assert MARCA not in _texto(msg)
    assert "incorrecta" in _texto(msg) or "Demasiados" in _texto(msg)


def test_control_positivo_con_login_correcto_si_hay_datos(servidor: tuple[gr.Blocks, str]) -> None:
    """Sin este control los tests de arriba podrían pasar por no saber leer la respuesta."""
    demo, url = servidor
    c = Cliente(url, demo)
    ok = c.llamar("entrar", [PASSWORD])
    assert MARCA in _texto(ok)
    assert PASSWORD not in _texto(ok)  # la contraseña nunca vuelve al cliente
    de_nuevo = c.llamar("actualizar", [None, "", False])  # el token sale del State de ESA sesión
    assert MARCA in _texto(de_nuevo)


def test_la_sesion_autorizada_no_se_filtra_a_otra_sesion(servidor: tuple[gr.Blocks, str]) -> None:
    demo, url = servidor
    a = Cliente(url, demo)
    assert MARCA in _texto(a.llamar("entrar", [PASSWORD]))
    b = a.nueva_sesion()
    assert MARCA not in _texto(b.llamar("actualizar", [None, "", False]))


def test_cerrar_sesion_revoca_el_acceso(servidor: tuple[gr.Blocks, str]) -> None:
    demo, url = servidor
    c = Cliente(url, demo)
    assert MARCA in _texto(c.llamar("entrar", [PASSWORD]))
    c.llamar("salir", [None])
    assert MARCA not in _texto(c.llamar("actualizar", [None, "", False]))


def test_bloqueo_por_intentos_aplica_tambien_por_http(tmp_path: Path) -> None:
    repo = Historial(tmp_path / "h.db")
    repo.registrar(MARCA, 0.9, False, 1.0, "0123456789abcdef")
    demo = app.construir_demo(None, repo, Administracion(password=PASSWORD))
    _, url, _ = demo.launch(prevent_thread_lock=True, quiet=True, server_port=None)
    try:
        for _ in range(3):
            Cliente(url, demo).llamar("entrar", ["mala"])  # sesiones distintas: el bloqueo es global
        msg = Cliente(url, demo).llamar("entrar", [PASSWORD])
        assert MARCA not in _texto(msg)
        assert "Demasiados intentos" in _texto(msg)
    finally:
        demo.close()


def test_sin_password_la_pestana_no_tiene_controles_ni_eventos(tmp_path: Path) -> None:
    demo = app.construir_demo(None, Historial(tmp_path / "h.db"), Administracion(password=""))
    nombres = {getattr(f, "name", None) for f in demo.fns.values()}
    assert not nombres & {"entrar", "actualizar", "exportar", "salir"}
