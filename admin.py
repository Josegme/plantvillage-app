"""Autenticación y acceso a datos de administración.

Principios:

* Fallar cerrado: sin ``ADMIN_PASSWORD`` no existe ninguna sesión válida.
* Ocultar una pestaña no es seguridad: TODA función que devuelve datos de
  administración exige un token de sesión y lo verifica en el servidor
  (``Administracion.verificar``), sea cual sea la vía por la que se la invoque.
* El token es aleatorio, se emite tras un login correcto y se guarda solo como
  hash SHA-256 en memoria. La contraseña nunca se guarda en el estado de sesión.
* El bloqueo por intentos fallidos es GLOBAL del proceso (no por sesión), con
  backoff exponencial en memoria.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import config
import historial
import metricas
from inferencia import Clasificador

logger = logging.getLogger(__name__)


class NoAutorizado(PermissionError):
    """Acceso denegado a una función de administración."""


class AdministracionDeshabilitada(NoAutorizado):
    """No hay contraseña configurada: la administración está cerrada."""


class Bloqueado(NoAutorizado):
    """Demasiados intentos fallidos; hay que esperar ``espera_s`` segundos."""

    def __init__(self, espera_s: float) -> None:
        super().__init__(f"Demasiados intentos fallidos. Espera {int(espera_s) + 1} s.")
        self.espera_s = espera_s


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Administracion:
    def __init__(
        self,
        password: str | None = None,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        if password is None:
            password = os.environ.get(config.VAR_PASSWORD_ADMIN)
        password = (password or "").strip()
        self._password: bytes | None = password.encode("utf-8") if password else None
        self._reloj = reloj
        self._lock = threading.Lock()
        self._fallos = 0
        self._bloqueado_hasta = 0.0
        self._tokens: dict[str, float] = {}  # hash del token -> expiración

    @property
    def habilitada(self) -> bool:
        return self._password is not None

    # --- login / sesión ---
    def iniciar_sesion(self, intento: str | None) -> str:
        """Devuelve un token de sesión o lanza ``NoAutorizado`` (o una subclase)."""
        if not self.habilitada:
            raise AdministracionDeshabilitada("La administración está deshabilitada en este despliegue.")
        with self._lock:
            ahora = self._reloj()
            if ahora < self._bloqueado_hasta:
                raise Bloqueado(self._bloqueado_hasta - ahora)
            candidato = (intento or "").encode("utf-8")
            if hmac.compare_digest(candidato, self._password or b""):
                self._fallos = 0
                self._bloqueado_hasta = 0.0
                return self._emitir_token(ahora)
            self._fallos += 1
            logger.warning("Intento de acceso a administración fallido (%d consecutivos).", self._fallos)
            exceso = self._fallos - config.INTENTOS_ANTES_DE_BLOQUEO
            if exceso >= 0:
                espera = min(config.BACKOFF_BASE_SEGUNDOS * 2**exceso, config.BACKOFF_MAX_SEGUNDOS)
                self._bloqueado_hasta = ahora + espera
            raise NoAutorizado("Contraseña incorrecta.")

    def _emitir_token(self, ahora: float) -> str:
        self._purgar(ahora)
        while len(self._tokens) >= config.MAX_TOKENS_ACTIVOS:
            self._tokens.pop(min(self._tokens, key=self._tokens.__getitem__))
        token = secrets.token_urlsafe(32)
        self._tokens[_hash_token(token)] = ahora + config.TTL_TOKEN_SEGUNDOS
        return token

    def _purgar(self, ahora: float) -> None:
        for h in [h for h, exp in self._tokens.items() if exp <= ahora]:
            del self._tokens[h]

    def verificar(self, token: object) -> None:
        """Lanza ``NoAutorizado`` salvo que ``token`` sea un token vigente emitido por este proceso."""
        if not self.habilitada:
            raise AdministracionDeshabilitada("La administración está deshabilitada en este despliegue.")
        if not isinstance(token, str) or not token:
            raise NoAutorizado("Sesión no válida.")
        candidato = _hash_token(token)
        with self._lock:
            ahora = self._reloj()
            self._purgar(ahora)
            valido = False
            for guardado in self._tokens:  # se recorren todos: sin salida anticipada
                valido |= hmac.compare_digest(candidato, guardado)
        if not valido:
            raise NoAutorizado("Sesión no válida o caducada.")

    def cerrar_sesion(self, token: object) -> None:
        if isinstance(token, str) and token:
            with self._lock:
                self._tokens.pop(_hash_token(token), None)


class PanelAdmin:
    """Datos de administración. Todos los métodos exigen un token válido."""

    def __init__(
        self,
        auth: Administracion,
        repositorio: historial.Historial,
        clasificador: Clasificador | None,
        dir_exportacion: Path | None = None,
    ) -> None:
        self.auth = auth
        self._historial = repositorio
        self._clasificador = clasificador
        self._dir_exportacion = dir_exportacion or (config.DATA_DIR / "exportaciones")

    def tabla(self, token: object, texto: str | None = None, solo_no_concluyentes: bool = False) -> list[historial.Fila]:
        self.auth.verificar(token)
        return self._historial.consultar(texto, solo_no_concluyentes)

    def exportar_csv(self, token: object, texto: str | None = None, solo_no_concluyentes: bool = False) -> Path:
        self.auth.verificar(token)
        contenido = historial.a_csv(self._historial.consultar(texto, solo_no_concluyentes))
        self._dir_exportacion.mkdir(parents=True, exist_ok=True)
        self._limpiar_exportaciones_antiguas()
        marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ruta = self._dir_exportacion / f"historial_{marca}_{secrets.token_hex(4)}.csv"
        ruta.write_text(contenido, encoding="utf-8", newline="")
        return ruta

    def _limpiar_exportaciones_antiguas(self, antiguedad_s: int = 600) -> None:
        limite = time.time() - antiguedad_s
        for ruta in self._dir_exportacion.glob("historial_*.csv"):
            try:
                if ruta.stat().st_mtime < limite:
                    ruta.unlink()
            except OSError:
                logger.warning("No se pudo limpiar una exportación antigua.")

    def metricas(self, token: object) -> list[list[str]]:
        self.auth.verificar(token)
        return metricas.metricas_en_filas()

    def reporte_por_clase(self, token: object) -> tuple[list[str], list[list[str]]]:
        self.auth.verificar(token)
        return metricas.cargar_reporte_por_clase()

    def matriz_confusion(self, token: object) -> str:
        self.auth.verificar(token)
        return str(config.RUTA_MATRIZ_CONFUSION)

    def info_modelo(self, token: object) -> dict[str, str]:
        self.auth.verificar(token)
        return self._clasificador.info() if self._clasificador else {}

    def clases(self, token: object) -> list[str]:
        self.auth.verificar(token)
        return list(self._clasificador.clases) if self._clasificador else []
