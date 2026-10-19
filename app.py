"""Punto de entrada: interfaz Gradio en español (Diagnóstico, Administración, Acerca de).

La lógica de negocio vive en los demás módulos; aquí solo se cablea la interfaz.
"""
from __future__ import annotations

import config  # primero: fija variables de entorno que leen TensorFlow y Gradio

import base64
import hashlib
import logging
import re
import uuid
from pathlib import Path

import gradio as gr

import contenido
import etiquetas
import historial
import metricas
import preprocesado
import presentacion
from admin import Administracion, Bloqueado, NoAutorizado, PanelAdmin
from inferencia import Clasificador, es_concluyente, obtener_clasificador, validar_umbral
from preprocesado import EntradaInvalida

logger = logging.getLogger("plantvillage")

AVISO = (
    "Herramienta demostrativa. No sustituye el diagnóstico de un profesional agronómico. "
    "El modelo se entrenó con imágenes de laboratorio (una sola hoja sobre fondo uniforme), "
    "por lo que puede fallar con fotos tomadas en campo o con objetos que no sean hojas."
)
AVISO_HISTORIAL = (
    "**Privacidad.** La copia temporal de tu imagen se elimina del servidor al terminar la consulta; "
    "si la subes y no llegas a diagnosticarla, se borra automáticamente en unos 6 minutos como máximo. "
    "Del historial solo se guardan metadatos de cada consulta (fecha UTC, hipótesis principal, "
    "confianza, si fue «no concluyente», latencia y una huella SHA-256 truncada de la imagen); "
    "la imagen nunca se guarda en él."
)
AVISO_ALMACENAMIENTO = (
    "ℹ️ En un Space gratuito de Hugging Face el almacenamiento es **efímero**: el historial "
    "puede perderse cuando el Space se reinicia."
)
MENSAJE_SIN_IMAGEN = "Sube o captura una imagen de una hoja y pulsa «Diagnosticar»."


def _pct(valor: float) -> str:
    return f"{valor * 100:.1f} %".replace(".", ",")


def _borrar_subida(ruta: str | Path) -> None:
    """Elimina la copia temporal de la subida, solo si está en el directorio temporal de Gradio."""
    try:
        destino = Path(ruta).resolve()
        if destino.is_file() and destino.is_relative_to(config.GRADIO_TMP_DIR.resolve()):
            destino.unlink()
    except OSError:
        logger.warning("No se pudo borrar una subida temporal.")  # sin nombres de archivo


_EXT_POR_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_DATA_URL = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=\s]+)$")


def _volcar_data_url(url: str) -> str | None:
    """Guarda una imagen recibida como data-URL en el directorio temporal; ``None`` si no es válida."""
    if len(url) > 4 * config.MAX_BYTES // 3 + 200:  # cota del tamaño en base64 de un archivo de 5 MB
        return None
    m = _DATA_URL.match(url)
    if not m:
        return None
    try:
        datos = base64.b64decode(m.group(2), validate=False)
    except ValueError:
        return None
    ruta = config.GRADIO_TMP_DIR / f"{uuid.uuid4().hex}{_EXT_POR_MIME[m.group(1)]}"
    ruta.write_bytes(datos)  # el tamaño máximo se comprueba después, en preprocesado.leer_bytes
    return str(ruta)


class ImagenSinDecodificar(gr.Image):
    """``gr.Image`` que entrega solo la ruta del archivo subido.

    El preprocesado de ``gr.Image`` abre el archivo con PIL antes de llegar a nuestro código;
    si la imagen está dañada o es una decompression bomb, Gradio vuelca un traceback con la ruta
    (y el nombre de archivo del usuario) al log y deja la copia temporal sin borrar. Aquí la
    validación la hace ``preprocesado``, que da un mensaje claro y no registra nombres.
    La comprobación de que la ruta pertenece a la caché de subidas sigue haciéndola Gradio
    antes de llamar a este método.
    """

    def get_block_name(self) -> str:
        return "image"  # el frontend identifica el componente por este nombre: reutiliza el de gr.Image

    def preprocess(self, payload):  # type: ignore[no-untyped-def,override]
        if payload is None:
            return None
        if payload.path:
            return payload.path
        if payload.url and payload.url.startswith("data:"):
            return _volcar_data_url(payload.url)
        return None


class Servicio:
    """Diagnóstico: valida, preprocesa, predice y registra solo metadatos."""

    def __init__(self, clasificador: Clasificador, repositorio: historial.Historial) -> None:
        self.clasificador = clasificador
        self.repositorio = repositorio
        # Gradio guarda copias de los ejemplos en su caché con el mismo formato que una subida:
        # no hay que borrarlas (son archivos del proyecto, no datos de usuario).
        self._hashes_ejemplos = {
            hashlib.sha256(p.read_bytes()).hexdigest() for p in config.DIR_EJEMPLOS.glob("*") if p.is_file()
        }

    def diagnosticar(self, ruta: str | None, umbral: float) -> str:
        """Devuelve el HTML del panel de resultado (o de un aviso de error)."""
        if not ruta:
            return presentacion.vacio(MENSAJE_SIN_IMAGEN)
        try:
            umbral = validar_umbral(umbral)
        except ValueError as e:
            _borrar_subida(ruta)
            return presentacion.alerta(str(e))
        conservar = False
        try:
            datos = preprocesado.leer_bytes(ruta)
            conservar = hashlib.sha256(datos).hexdigest() in self._hashes_ejemplos
            huella = preprocesado.hash_bytes(datos)
            x = preprocesado.preprocesar(preprocesado.decodificar(datos))
            pred = self.clasificador.predecir(x)
        except EntradaInvalida as e:
            return presentacion.alerta(str(e))
        except Exception as e:  # noqa: BLE001 - se informa al usuario sin filtrar detalles internos
            # Solo el tipo: el texto de la excepción puede incluir rutas/nombres de archivo.
            logger.error("Fallo inesperado en el diagnóstico (%s).", type(e).__name__)
            return presentacion.alerta("Ocurrió un error inesperado al procesar la imagen. Inténtalo de nuevo.")
        finally:
            if not conservar:
                _borrar_subida(ruta)

        top = pred.top1
        concluyente = es_concluyente(top.confianza, umbral)
        try:
            self.repositorio.registrar(top.clase, top.confianza, not concluyente, pred.latencia_ms, huella)
        except Exception as e:  # noqa: BLE001 - el historial no debe impedir el diagnóstico
            logger.error("No se pudo registrar la consulta (%s).", type(e).__name__)

        return presentacion.resultado(pred, umbral, concluyente)


def _texto_acerca(clasificador: Clasificador | None) -> str:
    debiles = metricas.clases_con_menor_recall(5)
    lista_debiles = "\n".join(f"- {etiquetas.nombre_legible(c)}: recall {_pct(r)}" for c, r in debiles)
    m = metricas.cargar_metricas()
    version = clasificador.version_modelo if clasificador else "no cargado"
    return f"""## Acerca de esta herramienta

Aplicación demostrativa que clasifica enfermedades en hojas de plantas (38 clases) a partir de una foto,
con un modelo MobileNetV2 con fine-tuning. Muestra las tres hipótesis más probables y la **confianza del modelo**.

### Datos
Entrenado con el conjunto **PlantVillage** (Hughes y Salathé, 2015, *An open access repository of images on
plant health to enable the development of mobile disease diagnostics*, arXiv:1511.08060), publicado por
el proyecto PlantVillage (Penn State University y EPFL). Todo el mérito del conjunto de datos corresponde a sus autores.

### Rendimiento medido en el conjunto de test
Las cifras de la tabla siguiente se leen de los archivos de evaluación del modelo (`modelo/metricas_test.json`).

### Limitaciones, en lenguaje claro
- Se entrenó con fotos de laboratorio: una hoja, fondo uniforme. Con fotos de campo rinde peor.
- No sabe decir «esto no es una hoja»: ante cualquier imagen siempre propondrá alguna de las 38 clases.
- La confianza que muestra no es una medida calibrada de acierto: un valor alto no garantiza que el diagnóstico sea correcto.
- Puede confundir enfermedades parecidas. Las clases con menor recall en test son:
{lista_debiles}
- Una hoja enferma puede ser clasificada como sana: ocurrió en {m["enfermas_predichas_sanas_test"]} de {m["enfermas_test"]} hojas enfermas de test.

### Versión del modelo
`{version}`

### Repositorio
{config.REPOSITORIO_URL}
"""


def construir_demo(
    clasificador: Clasificador | None,
    repositorio: historial.Historial,
    auth: Administracion,
) -> gr.Blocks:
    """Construye la interfaz. ``clasificador`` puede ser un doble en tests."""
    servicio = Servicio(clasificador, repositorio) if clasificador is not None else None
    panel = PanelAdmin(auth, repositorio, clasificador)

    def diagnosticar(ruta: str | None, umbral: float) -> str:
        if servicio is None:
            return presentacion.alerta("El modelo no está disponible.")
        return servicio.diagnosticar(ruta, umbral)

    with gr.Blocks(title="Diagnóstico de hojas · PlantVillage", delete_cache=config.DELETE_CACHE) as demo:
        gr.HTML(presentacion.cabecera())
        gr.HTML(presentacion.aviso_permanente(AVISO))  # fuera de las pestañas: visible siempre

        with gr.Tabs():
            # ---------------------------------------------------------- Diagnóstico
            with gr.Tab("Diagnóstico"):
                with gr.Row():
                    with gr.Column():
                        imagen = ImagenSinDecodificar(
                            label="Foto de la hoja",
                            sources=["upload", "webcam"],
                            type="filepath",
                            height=360,
                        )
                        umbral = gr.Slider(
                            0.0, 1.0, value=config.UMBRAL_CONFIANZA_DEFECTO, step=0.01,
                            label="Umbral de confianza",
                            info="Por debajo de este valor el resultado se marca como «no concluyente».",
                        )
                        boton = gr.Button("Diagnosticar", variant="primary")
                    with gr.Column():
                        resultado = gr.HTML(presentacion.vacio(MENSAJE_SIN_IMAGEN))
                ejemplos = sorted(config.DIR_EJEMPLOS.glob("*.jpg"))
                gr.Examples(
                    examples=[[str(p)] for p in ejemplos],
                    example_labels=[p.stem.replace("_", " ") for p in ejemplos],
                    inputs=[imagen],
                    label="Ejemplos (haz clic y pulsa «Diagnosticar»)",
                    cache_examples=False,
                )
                boton.click(diagnosticar, [imagen, umbral], [resultado], api_name="diagnosticar")
                gr.Markdown(AVISO_HISTORIAL)

            # ------------------------------------------------------ Textos explicativos
            with gr.Tab("Para qué sirve"):
                gr.Markdown(contenido.cargar("para_que_sirve"), elem_classes=["pv-lectura"])
            with gr.Tab("Cómo se hizo"):
                gr.Markdown(contenido.cargar("como_se_hizo"), elem_classes=["pv-lectura"])

            # ------------------------------------------------------- Administración
            with gr.Tab("Administración"):
                gr.Markdown(AVISO_ALMACENAMIENTO)
                if not auth.habilitada:
                    gr.Markdown(
                        "🔒 La administración está **deshabilitada** en este despliegue "
                        f"(no se definió la variable de entorno `{config.VAR_PASSWORD_ADMIN}`)."
                    )
                else:
                    _construir_pestana_admin(panel, auth)

            # ------------------------------------------------------------ Acerca de
            with gr.Tab("Acerca de"):
                gr.Markdown(_texto_acerca(clasificador))
                cab_m = ["Métrica", "Valor"]
                gr.Dataframe(value=metricas.metricas_en_filas(), headers=cab_m, interactive=False, label="Métricas de test")

    demo.queue(max_size=20, default_concurrency_limit=2)
    return demo


def _construir_pestana_admin(panel: PanelAdmin, auth: Administracion) -> None:
    """Pestaña protegida. Cada evento verifica el token en el servidor; ninguno se expone como API."""
    token = gr.State(None)  # token de sesión aleatorio (no la contraseña); vive en el servidor

    with gr.Group():
        clave = gr.Textbox(label="Contraseña de administración", type="password")
        entrar_btn = gr.Button("Entrar", variant="primary")
        estado = gr.Markdown()

    with gr.Column(visible=False) as contenido:
        salir_btn = gr.Button("Cerrar sesión")
        gr.Markdown("### Historial de consultas")
        with gr.Row():
            filtro = gr.Textbox(label="Filtrar por clase o huella", scale=3)
            solo_nc = gr.Checkbox(label="Solo no concluyentes", scale=1)
            actualizar_btn = gr.Button("Actualizar", scale=1)
        tabla = gr.Dataframe(headers=list(historial.COLUMNAS), interactive=False, max_height=360)
        with gr.Row():
            csv_btn = gr.Button("Generar CSV")
            csv_archivo = gr.File(label="CSV generado", interactive=False)
        gr.Markdown("### Métricas del modelo (leídas de `modelo/`)")
        m_tabla = gr.Dataframe(headers=["Métrica", "Valor"], interactive=False)
        gr.Markdown("### Métricas por clase")
        r_tabla = gr.Dataframe(interactive=False, max_height=360)
        gr.Markdown("### Matriz de confusión (test)")
        matriz = gr.Image(type="filepath", interactive=False, show_label=False)
        gr.Markdown("### Modelo")
        info = gr.JSON(label="Versión y entorno")
        clases = gr.Dataframe(headers=["Clase"], interactive=False, max_height=300)

    datos = [tabla, m_tabla, r_tabla, matriz, info, clases]

    def _vacio() -> list:
        return [gr.update() for _ in datos]

    def _cargar(t: object, texto: str | None, solo: bool) -> list:
        filas = panel.tabla(t, texto, solo)
        cab, rep = panel.reporte_por_clase(t)
        return [
            filas,
            panel.metricas(t),
            {"headers": cab, "data": rep},
            panel.matriz_confusion(t),
            panel.info_modelo(t),
            [[c] for c in panel.clases(t)],
        ]

    def entrar(clave_intentada: str):
        try:
            t = auth.iniciar_sesion(clave_intentada)
        except Bloqueado as e:
            return [None, f"⛔ {e}", gr.update(visible=False), "", *_vacio()]
        except NoAutorizado as e:
            return [None, f"❌ {e}", gr.update(visible=False), "", *_vacio()]
        return [t, "✅ Sesión iniciada.", gr.update(visible=True), "", *_cargar(t, None, False)]

    def actualizar(t: object, texto: str | None, solo: bool):
        try:
            return [t, "", gr.update(), *_cargar(t, texto, solo)]
        except NoAutorizado:
            return [None, "⚠️ Sesión no válida o caducada. Vuelve a entrar.", gr.update(visible=False), *_vacio()]

    def exportar(t: object, texto: str | None, solo: bool):
        try:
            return str(panel.exportar_csv(t, texto, solo))
        except NoAutorizado:
            return None

    def salir(t: object):
        auth.cerrar_sesion(t)
        return [None, "Sesión cerrada.", gr.update(visible=False), *_vacio()]

    salida_sesion = [token, estado, contenido]
    entrar_btn.click(entrar, [clave], [*salida_sesion, clave, *datos], api_name=False)
    clave.submit(entrar, [clave], [*salida_sesion, clave, *datos], api_name=False)
    actualizar_btn.click(actualizar, [token, filtro, solo_nc], [*salida_sesion, *datos], api_name=False)
    csv_btn.click(exportar, [token, filtro, solo_nc], [csv_archivo], api_name=False)
    salir_btn.click(salir, [token], [*salida_sesion, *datos], api_name=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for ruidoso in ("httpx", "httpcore"):  # registran URLs de peticiones internas
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    clasificador = obtener_clasificador()  # carga y calentamiento al arrancar (no lazy)
    demo = construir_demo(clasificador, historial.Historial(), Administracion())
    demo.launch(
        max_file_size=config.MAX_BYTES,
        show_error=False,
        footer_links=["gradio"],
        theme=presentacion.crear_tema(),
        css_paths=[presentacion.RUTA_CSS],
        js=presentacion.JS_TEMA_CLARO,
    )


if __name__ == "__main__":
    main()
