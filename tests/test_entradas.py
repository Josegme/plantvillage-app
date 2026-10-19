"""(d) Rechazo de entradas inválidas."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

import config
import preprocesado
from preprocesado import EntradaInvalida


def _guardar(ruta: Path, formato: str, tam: tuple[int, int] = (64, 64)) -> Path:
    Image.new("RGB", tam, (10, 120, 10)).save(ruta, format=formato)
    return ruta


@pytest.mark.parametrize(("nombre", "formato"), [("a.jpg", "JPEG"), ("a.jpeg", "JPEG"), ("a.png", "PNG"), ("a.webp", "WEBP")])
def test_formatos_validos(tmp_path: Path, nombre: str, formato: str) -> None:
    datos = preprocesado.leer_bytes(_guardar(tmp_path / nombre, formato))
    assert preprocesado.decodificar(datos).size == (64, 64)


def test_extension_no_permitida(tmp_path: Path) -> None:
    ruta = tmp_path / "a.gif"
    Image.new("RGB", (8, 8)).save(ruta, format="GIF")
    with pytest.raises(EntradaInvalida, match="Formato no admitido"):
        preprocesado.leer_bytes(ruta)


def test_extension_engañosa_se_detecta_por_el_formato_real(tmp_path: Path) -> None:
    ruta = tmp_path / "falso.png"
    Image.new("RGB", (8, 8)).save(ruta, format="GIF")
    with pytest.raises(EntradaInvalida, match="Formato no admitido"):
        preprocesado.decodificar(preprocesado.leer_bytes(ruta))


def test_archivo_vacio(tmp_path: Path) -> None:
    ruta = tmp_path / "vacio.jpg"
    ruta.write_bytes(b"")
    with pytest.raises(EntradaInvalida, match="vacío"):
        preprocesado.leer_bytes(ruta)


def test_archivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(EntradaInvalida):
        preprocesado.leer_bytes(tmp_path / "no_existe.jpg")


def test_supera_5_mb(tmp_path: Path) -> None:
    ruta = tmp_path / "grande.jpg"
    ruta.write_bytes(b"\xff\xd8\xff" + b"0" * (config.MAX_BYTES + 10))
    with pytest.raises(EntradaInvalida, match="máximo de 5 MB"):
        preprocesado.leer_bytes(ruta)


def test_exactamente_5_mb_se_lee(tmp_path: Path) -> None:
    ruta = tmp_path / "justo.jpg"
    ruta.write_bytes(b"0" * config.MAX_BYTES)
    assert len(preprocesado.leer_bytes(ruta)) == config.MAX_BYTES


def test_imagen_corrupta(tmp_path: Path) -> None:
    ruta = tmp_path / "rota.jpg"
    ruta.write_bytes(b"esto no es una imagen")
    with pytest.raises(EntradaInvalida, match="No se pudo leer"):
        preprocesado.decodificar(preprocesado.leer_bytes(ruta))


def test_imagen_truncada(tmp_path: Path) -> None:
    buf = io.BytesIO()
    Image.effect_noise((200, 200), 80).convert("RGB").save(buf, format="JPEG")
    with pytest.raises(EntradaInvalida, match="No se pudo leer"):
        preprocesado.decodificar(buf.getvalue()[: len(buf.getvalue()) // 2])


def test_decompression_bomb(tmp_path: Path) -> None:
    """PNG liso de ~36 MP: pesa poco pero excede MAX_PIXELES."""
    ruta = tmp_path / "bomba.png"
    Image.new("L", (6000, 6000)).save(ruta, format="PNG", compress_level=9)
    assert ruta.stat().st_size < config.MAX_BYTES
    assert 6000 * 6000 > config.MAX_PIXELES
    with pytest.raises(EntradaInvalida, match="demasiados píxeles"):
        preprocesado.decodificar(preprocesado.leer_bytes(ruta))


def test_bomba_extrema_tambien_se_rechaza(tmp_path: Path) -> None:
    """Más de 2x el límite: Pillow lanza DecompressionBombError al abrir."""
    ruta = tmp_path / "bomba2.png"
    Image.new("1", (20000, 20000)).save(ruta, format="PNG", compress_level=9)
    with pytest.raises(EntradaInvalida, match="demasiados píxeles"):
        preprocesado.decodificar(preprocesado.leer_bytes(ruta))


def test_hash_es_truncado_y_estable() -> None:
    h = preprocesado.hash_bytes(b"abc")
    assert h == preprocesado.hash_bytes(b"abc")
    assert len(h) == config.LONGITUD_HASH
    assert h != preprocesado.hash_bytes(b"abd")
