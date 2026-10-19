"""Lógica del diagnóstico (umbral en la salida, historial, privacidad de temporales y logs)."""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import app
import config
from historial import Historial
from inferencia import Hipotesis, Prediccion


class ClasificadorFalso:
    """Devuelve una predicción fija; evita cargar el modelo real."""

    def __init__(self, confianza: float = 0.9, error: Exception | None = None) -> None:
        self.confianza = confianza
        self.error = error
        self.version_modelo = "falso@0"
        self.clases = ["Tomato___Early_blight", "Tomato___healthy", "Apple___healthy"]

    def predecir(self, x: np.ndarray) -> Prediccion:
        if self.error:
            raise self.error
        resto = (1 - self.confianza) / 2
        hip = (
            Hipotesis(0, "Tomato___Early_blight", self.confianza),
            Hipotesis(1, "Tomato___healthy", resto),
            Hipotesis(2, "Apple___healthy", resto),
        )
        return Prediccion(hip, 12.0)


@pytest.fixture
def repo(tmp_path: Path) -> Historial:
    return Historial(tmp_path / "h.db")


@pytest.fixture
def foto(tmp_path: Path) -> Path:
    ruta = tmp_path / "foto_privada_del_usuario.jpg"
    Image.new("RGB", (80, 60), (30, 140, 30)).save(ruta)
    return ruta


def _servicio(repo: Historial, **kw) -> app.Servicio:
    return app.Servicio(ClasificadorFalso(**kw), repo)


def test_resultado_concluyente_usa_confianza_y_registra(repo: Historial, foto: Path) -> None:
    resumen, filas = _servicio(repo, confianza=0.9).diagnosticar(str(foto), 0.6)
    assert "Confianza del modelo" in resumen and "90,0 %" in resumen
    assert "no concluyente" not in resumen.lower()
    assert [f[1] for f in filas] == ["Tomate — Tizón temprano", "Tomate — Sana", "Manzana — Sana"]
    (fila,) = repo.consultar()
    assert fila[2] == "Tomato___Early_blight" and fila[4] == 0 and len(fila[6]) == config.LONGITUD_HASH


def test_resultado_no_concluyente_sigue_mostrando_top3(repo: Historial, foto: Path) -> None:
    resumen, filas = _servicio(repo, confianza=0.5).diagnosticar(str(foto), 0.6)
    assert "Resultado no concluyente" in resumen
    assert len(filas) == 3
    assert repo.consultar()[0][4] == 1


def test_umbral_exacto_es_concluyente(repo: Historial, foto: Path) -> None:
    resumen, _ = _servicio(repo, confianza=0.6).diagnosticar(str(foto), 0.6)
    assert "Resultado no concluyente" not in resumen


def test_umbral_cambiado_por_el_usuario(repo: Historial, foto: Path) -> None:
    servicio = _servicio(repo, confianza=0.7)
    assert "no concluyente" not in servicio.diagnosticar(str(foto), 0.6)[0].lower()
    assert "Resultado no concluyente" in servicio.diagnosticar(str(foto), 0.8)[0]


def test_nunca_aparece_la_palabra_probabilidad(repo: Historial, foto: Path) -> None:
    textos = [app.AVISO, app.AVISO_HISTORIAL, app.AVISO_ALMACENAMIENTO, app.MENSAJE_SIN_IMAGEN, app._texto_acerca(None)]
    for conf in (0.9, 0.3):
        resumen, filas = _servicio(repo, confianza=conf).diagnosticar(str(foto), 0.6)
        textos += [resumen, *(c for f in filas for c in f)]
    assert not any(re.search("probabilidad", t, re.IGNORECASE) for t in textos)


def test_sin_imagen_no_registra(repo: Historial) -> None:
    resumen, filas = _servicio(repo).diagnosticar(None, 0.6)
    assert resumen == app.MENSAJE_SIN_IMAGEN and filas == []
    assert repo.contar() == 0


@pytest.mark.parametrize("umbral", [float("nan"), -1, 2, "x"])
def test_umbral_invalido_da_mensaje_y_no_registra(repo: Historial, foto: Path, umbral: object) -> None:
    resumen, filas = _servicio(repo).diagnosticar(str(foto), umbral)  # type: ignore[arg-type]
    assert resumen.startswith("❌") and filas == []
    assert repo.contar() == 0


def test_entradas_invalidas_dan_mensaje_claro_y_no_registran(repo: Historial, tmp_path: Path) -> None:
    mala = tmp_path / "rota.png"
    mala.write_bytes(b"no soy una imagen")
    gif = tmp_path / "a.gif"
    Image.new("RGB", (4, 4)).save(gif)
    for ruta in (mala, gif, tmp_path / "no_existe.jpg"):
        resumen, filas = _servicio(repo).diagnosticar(str(ruta), 0.6)
        assert resumen.startswith("❌") and filas == []
    assert repo.contar() == 0


# --- privacidad: copias temporales y logs ---
@pytest.fixture
def subida_en_cache() -> Path:
    destino = config.GRADIO_TMP_DIR / "hash_de_prueba_subida"
    destino.mkdir(parents=True, exist_ok=True)
    yield destino
    shutil.rmtree(destino, ignore_errors=True)


def test_la_copia_temporal_de_la_subida_se_borra_tras_la_consulta(repo: Historial, subida_en_cache: Path, foto: Path) -> None:
    copia = subida_en_cache / "foto_privada.jpg"
    shutil.copy(foto, copia)
    _servicio(repo).diagnosticar(str(copia), 0.6)
    assert not copia.exists()


def test_la_copia_temporal_se_borra_tambien_si_la_imagen_es_invalida(repo: Historial, subida_en_cache: Path) -> None:
    copia = subida_en_cache / "rota.jpg"
    copia.write_bytes(b"xx")
    _servicio(repo).diagnosticar(str(copia), 0.6)
    assert not copia.exists()


def test_la_copia_temporal_se_borra_si_falla_la_inferencia(repo: Historial, subida_en_cache: Path, foto: Path) -> None:
    copia = subida_en_cache / "foto.jpg"
    shutil.copy(foto, copia)
    _servicio(repo, error=RuntimeError("boom")).diagnosticar(str(copia), 0.6)
    assert not copia.exists()


def test_no_se_borran_archivos_fuera_del_directorio_temporal(repo: Historial, foto: Path) -> None:
    _servicio(repo).diagnosticar(str(foto), 0.6)
    assert foto.exists()


def test_no_se_borran_las_copias_de_los_ejemplos(repo: Historial, subida_en_cache: Path) -> None:
    ejemplo = sorted(config.DIR_EJEMPLOS.glob("*.jpg"))[0]
    copia = subida_en_cache / ejemplo.name
    shutil.copy(ejemplo, copia)
    _servicio(repo).diagnosticar(str(copia), 0.6)
    assert copia.exists()


def test_los_logs_no_contienen_nombres_de_archivo(repo: Historial, subida_en_cache: Path, foto: Path, caplog: pytest.LogCaptureFixture) -> None:
    copia = subida_en_cache / "nombre_secreto_del_usuario.jpg"
    shutil.copy(foto, copia)
    caplog.set_level(logging.DEBUG)
    # Una excepción cuyo mensaje incluye la ruta (como hacen los OSError reales).
    _servicio(repo, error=FileNotFoundError(2, "No such file", str(copia))).diagnosticar(str(copia), 0.6)
    resumen, _ = _servicio(repo, error=RuntimeError(f"fallo con {copia}")).diagnosticar(str(copia), 0.6)
    assert "nombre_secreto" not in caplog.text
    assert "nombre_secreto" not in resumen
    assert caplog.records, "se esperaba al menos un registro de error"


# --- componente de imagen: no debe abrir el archivo (evita tracebacks con nombres de archivo) ---
def test_el_componente_entrega_la_ruta_sin_abrir_el_archivo(tmp_path: Path) -> None:
    from gradio.data_classes import ImageData

    rota = tmp_path / "rota_nombre_usuario.jpg"
    rota.write_bytes(b"no es una imagen")
    componente = app.ImagenSinDecodificar(type="filepath")
    assert componente.preprocess(ImageData(path=str(rota), orig_name=rota.name)) == str(rota)
    assert componente.preprocess(None) is None


def test_el_componente_acepta_data_url_valida_y_rechaza_el_resto() -> None:
    import base64
    import io

    from gradio.data_classes import ImageData

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="PNG")
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    componente = app.ImagenSinDecodificar(type="filepath")
    ruta = componente.preprocess(ImageData(url=url))
    try:
        assert ruta and Path(ruta).read_bytes() == buf.getvalue()
        assert Path(ruta).resolve().is_relative_to(config.GRADIO_TMP_DIR.resolve())
    finally:
        if ruta:
            Path(ruta).unlink(missing_ok=True)
    assert componente.preprocess(ImageData(url="data:text/html;base64,PGI+")) is None
    assert componente.preprocess(ImageData(url="data:image/png;base64," + "A" * (4 * config.MAX_BYTES // 3 + 500))) is None


def test_el_plazo_de_borrado_anunciado_en_la_interfaz_es_cierto() -> None:
    """La interfaz dice «unos 6 minutos como máximo»: barrido + antigüedad no puede superarlo."""
    frecuencia, antiguedad = config.DELETE_CACHE
    assert frecuencia + antiguedad <= 6 * 60
    assert "6 minutos" in app.AVISO_HISTORIAL


def test_el_componente_se_identifica_como_image_para_el_frontend() -> None:
    assert app.ImagenSinDecodificar().get_block_name() == "image"
