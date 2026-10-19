"""(e) El acceso a administración falla sin contraseña correcta."""
from __future__ import annotations

from pathlib import Path

import pytest

import config
from admin import Administracion, AdministracionDeshabilitada, Bloqueado, NoAutorizado, PanelAdmin
from historial import Historial


class Reloj:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def auth(reloj: Reloj) -> Administracion:
    return Administracion(password="secreto-correcto", reloj=reloj)


@pytest.fixture
def panel(auth: Administracion, tmp_path: Path) -> PanelAdmin:
    repo = Historial(tmp_path / "h.db")
    repo.registrar("Tomato___healthy", 0.97, False, 12.5, "abcdef0123456789")
    return PanelAdmin(auth, repo, clasificador=None, dir_exportacion=tmp_path / "exp")


def test_sin_variable_de_entorno_queda_deshabilitada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.VAR_PASSWORD_ADMIN, raising=False)
    auth = Administracion()
    assert not auth.habilitada
    with pytest.raises(AdministracionDeshabilitada):
        auth.iniciar_sesion("cualquiera")
    with pytest.raises(AdministracionDeshabilitada):
        auth.iniciar_sesion("")
    with pytest.raises(AdministracionDeshabilitada):
        auth.verificar("token-inventado")


@pytest.mark.parametrize("valor", ["", "   "])
def test_contrasena_vacia_equivale_a_no_definida(monkeypatch: pytest.MonkeyPatch, valor: str) -> None:
    monkeypatch.setenv(config.VAR_PASSWORD_ADMIN, valor)
    assert not Administracion().habilitada


def test_lee_la_contrasena_de_la_variable_de_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.VAR_PASSWORD_ADMIN, "desde-entorno")
    auth = Administracion()
    assert auth.habilitada
    auth.verificar(auth.iniciar_sesion("desde-entorno"))


def test_login_correcto_emite_token_aleatorio_distinto_de_la_contrasena(auth: Administracion) -> None:
    t1, t2 = auth.iniciar_sesion("secreto-correcto"), auth.iniciar_sesion("secreto-correcto")
    assert t1 != t2
    assert "secreto-correcto" not in (t1, t2) and len(t1) >= 32
    auth.verificar(t1)
    auth.verificar(t2)


@pytest.mark.parametrize("intento", ["", "mala", None, "secreto-correcto ", "SECRETO-CORRECTO", "ñandú-ñ"])
def test_contrasena_incorrecta(auth: Administracion, intento: str | None) -> None:
    with pytest.raises(NoAutorizado):
        auth.iniciar_sesion(intento)


@pytest.mark.parametrize("token", [None, "", "inventado", 123, b"bytes", ["x"], "secreto-correcto"])
def test_token_invalido_o_la_propia_contrasena_no_valen(auth: Administracion, token: object) -> None:
    auth.iniciar_sesion("secreto-correcto")
    with pytest.raises(NoAutorizado):
        auth.verificar(token)


def test_token_caduca(auth: Administracion, reloj: Reloj) -> None:
    token = auth.iniciar_sesion("secreto-correcto")
    reloj.t += config.TTL_TOKEN_SEGUNDOS - 1
    auth.verificar(token)
    reloj.t += 2
    with pytest.raises(NoAutorizado):
        auth.verificar(token)


def test_cerrar_sesion_invalida_el_token(auth: Administracion) -> None:
    token = auth.iniciar_sesion("secreto-correcto")
    auth.cerrar_sesion(token)
    with pytest.raises(NoAutorizado):
        auth.verificar(token)


def test_limite_de_tokens_activos(auth: Administracion) -> None:
    tokens = [auth.iniciar_sesion("secreto-correcto") for _ in range(config.MAX_TOKENS_ACTIVOS + 5)]
    with pytest.raises(NoAutorizado):
        auth.verificar(tokens[0])
    auth.verificar(tokens[-1])


def test_bloqueo_global_con_backoff(auth: Administracion, reloj: Reloj) -> None:
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEO):
        with pytest.raises(NoAutorizado):
            auth.iniciar_sesion("mala")
    # Bloqueado: incluso la contraseña correcta se rechaza hasta que pase la espera.
    with pytest.raises(Bloqueado) as e1:
        auth.iniciar_sesion("secreto-correcto")
    assert e1.value.espera_s == pytest.approx(config.BACKOFF_BASE_SEGUNDOS)
    reloj.t += config.BACKOFF_BASE_SEGUNDOS + 0.1
    # Un nuevo fallo duplica la espera.
    with pytest.raises(NoAutorizado):
        auth.iniciar_sesion("mala")
    with pytest.raises(Bloqueado) as e2:
        auth.iniciar_sesion("secreto-correcto")
    assert e2.value.espera_s == pytest.approx(config.BACKOFF_BASE_SEGUNDOS * 2)
    reloj.t += config.BACKOFF_BASE_SEGUNDOS * 2 + 0.1
    auth.verificar(auth.iniciar_sesion("secreto-correcto"))
    # Tras un login correcto se reinicia el contador.
    with pytest.raises(NoAutorizado) as e3:
        auth.iniciar_sesion("mala")
    assert not isinstance(e3.value, Bloqueado)


def test_el_bloqueo_es_global_no_por_sesion(auth: Administracion) -> None:
    """Da igual quién intente: el contador pertenece a la instancia (proceso)."""
    for _ in range(config.INTENTOS_ANTES_DE_BLOQUEO):
        with pytest.raises(NoAutorizado):
            auth.iniciar_sesion("mala")
    with pytest.raises(Bloqueado):
        auth.iniciar_sesion("otra-sesion-distinta")


def test_backoff_con_tope(auth: Administracion, reloj: Reloj) -> None:
    for _ in range(40):
        reloj.t += config.BACKOFF_MAX_SEGUNDOS + 1
        with pytest.raises(NoAutorizado):
            auth.iniciar_sesion("mala")
    with pytest.raises(Bloqueado) as e:
        auth.iniciar_sesion("secreto-correcto")
    assert e.value.espera_s <= config.BACKOFF_MAX_SEGUNDOS


# --- toda función que devuelve datos de administración exige token ---
_FUNCIONES = ["tabla", "exportar_csv", "metricas", "reporte_por_clase", "matriz_confusion", "info_modelo", "clases"]


@pytest.mark.parametrize("nombre", _FUNCIONES)
@pytest.mark.parametrize("token", [None, "", "falso", 0])
def test_funciones_de_admin_rechazan_tokens_invalidos(panel: PanelAdmin, nombre: str, token: object) -> None:
    with pytest.raises(NoAutorizado):
        getattr(panel, nombre)(token)


@pytest.mark.parametrize("nombre", _FUNCIONES)
def test_funciones_de_admin_deshabilitadas_sin_password(tmp_path: Path, nombre: str) -> None:
    sin = PanelAdmin(Administracion(password=""), Historial(tmp_path / "h.db"), None, tmp_path / "exp")
    with pytest.raises(AdministracionDeshabilitada):
        getattr(sin, nombre)("cualquiera")


def test_funciones_de_admin_con_token_valido(panel: PanelAdmin) -> None:
    token = panel.auth.iniciar_sesion("secreto-correcto")
    assert len(panel.tabla(token)) == 1
    assert panel.metricas(token)
    assert panel.reporte_por_clase(token)[1]
    assert Path(panel.matriz_confusion(token)).exists()
    assert panel.exportar_csv(token).read_text(encoding="utf-8").startswith("id,timestamp_utc")
