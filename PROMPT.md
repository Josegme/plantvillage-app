# ROL
Actúa como ingeniero senior de ML/Python con experiencia en aplicaciones Gradio en producción
y despliegue en Hugging Face Spaces (CPU). Prioriza código limpio, tipado, testeable y seguro.

# OBJETIVO
Construir una aplicación web en español que clasifique enfermedades en hojas de plantas
(38 clases de PlantVillage) a partir de una foto, usando un modelo Keras ya entrenado,
con una pestaña de administración. Debe quedar lista para desplegar en Hugging Face Spaces.

# CONTEXTO (no cambiar nada de esto)
- Modelo: `modelo/plantvillage_mobilenetv2.keras` (Keras 3, MobileNetV2 con fine-tuning).
  Entrada (None,224,224,3), float32 con valores CRUDOS 0–255. El reescalado a [-1,1] y la
  capa de aumento ya están DENTRO del modelo: NO normalizar fuera. Salida: softmax de 38 clases.
- `modelo/class_names.json`: nombres de clase en el orden exacto de los índices del modelo
  (formato `Cultivo___Enfermedad`, p. ej. `Tomato___Early_blight`, `Apple___healthy`).
- `modelo/metricas_test.json` y `modelo/reporte_test_por_clase.csv`: métricas reales en test.
  Léelas desde estos archivos; NO escribas cifras de rendimiento a mano en el código.
- `modelo/ejemplos/`: 8 imágenes de demostración.
- Preprocesado de referencia, validado contra la evaluación (99,67% de coincidencia en 300 imágenes):
    img = ImageOps.exif_transpose(img).convert("RGB")
    arr = tf.image.resize(np.array(img), (224, 224)).numpy()   # remuestreo igual al del entrenamiento
    x = arr[None, ...].astype("float32")
  Úsalo tal cual. No lo sustituyas por PIL.resize ni cambies el remuestreo.
- Versiones (fijar exactamente en requirements.txt; CPU únicamente):
  - Versiones de entrenamiento (referencia): python 3.13.15 | tensorflow 2.21.0 | keras 3.13.2 | numpy 2.1.3 | pillow 11.3.0
  - En requirements.txt fijar con == tensorflow-cpu (2.21.0), keras (3.13.2), numpy (2.1.3) y pillow (11.3.0). TensorFlow y Keras deben coincidir exactamente porque determinan si el .keras carga; si no se puede resolver con el Python local, avisa y no cambies esas versiones por tu cuenta.
- Limitaciones conocidas del modelo: entrenado con fotos de laboratorio (una hoja, fondo uniforme);
  rinde peor en campo. Clases más débiles: Tomato Early blight (recall 0,77), Tomato Septoria,
  Corn Cercospora vs Northern Leaf Blight, Tomato mosaic virus. Hojas enfermas predichas como
  sanas: 8 de 3923 en test. El softmax NO es una probabilidad calibrada y el modelo no puede
  decir "esto no es una hoja".

# ALCANCE FUNCIONAL
Interfaz Gradio en español, con 3 pestañas.

1. **Diagnóstico**
   - Carga de imagen (subida y cámara). Validar: formato jpg/jpeg/png/webp, máx. 5 MB,
     límite de píxeles contra decompression bombs, imagen decodificable. Mensajes de error claros.
   - Mostrar las 3 hipótesis más probables con nombre legible en español (cultivo + estado) y
     "confianza del modelo" en %, nunca la palabra "probabilidad".
   - Umbral de confianza configurable (por defecto 0,60): si la top-1 queda por debajo, mostrar
     "Resultado no concluyente" en lugar de un diagnóstico firme, y seguir mostrando el top-3.
   - Aviso visible y permanente: herramienta demostrativa, no sustituye diagnóstico agronómico;
     entrenada con imágenes de laboratorio; puede fallar con fotos de campo u objetos que no sean hojas.
   - Galería de ejemplos clicables desde `modelo/ejemplos/`.
   - Diccionario de traducción cultivo/enfermedad en un módulo aparte (`etiquetas.py`),
     con test que verifique que cubre las 38 clases.

2. **Administración** (protegida)
   - Contraseña desde la variable de entorno `ADMIN_PASSWORD`. Si no está definida, la pestaña
     queda deshabilitada (fallar cerrado). Comparar con `hmac.compare_digest`.
   - IMPORTANTE: ocultar una pestaña NO es seguridad. Toda función que devuelva datos de
     administración debe verificar la autorización en el servidor.
   - Contenido: historial de consultas (tabla filtrable), descarga en CSV, métricas del modelo
     (leídas de los archivos de `modelo/`), matriz de confusión, versión del modelo y lista de clases.
   - Historial en SQLite (stdlib). Cada registro guarda SOLO metadatos: marca de tiempo UTC,
     top-1, confianza, flag de "no concluyente", latencia, hash SHA-256 truncado de los bytes
     de la imagen. NUNCA guardar la imagen ni datos del usuario.
   - Al exportar CSV, neutralizar la inyección de fórmulas (prefijar con `'` las celdas que
     empiecen por `=`, `+`, `-` o `@`).
   - Indicar en la UI que, en Spaces gratuito, el almacenamiento es efímero y el historial
     puede perderse al reiniciar.

3. **Acerca de**
   - Descripción, dataset (PlantVillage; atribución al origen), métricas de test (desde archivos),
     limitaciones en lenguaje claro, versión del modelo y repositorio.

# RESTRICCIONES TÉCNICAS
- Python con type hints. Módulos separados: `app.py` (punto de entrada, requerido por Spaces),
  `inferencia.py` (carga del modelo una sola vez y predicción), `preprocesado.py`,
  `etiquetas.py`, `historial.py`, `config.py` (umbral, límites, rutas).
- Sin reentrenar ni modificar el modelo. Sin servicios externos ni llamadas de red en inferencia.
- Logging estándar, sin imprimir datos sensibles. Manejo explícito de excepciones.
- Sin secretos en el repositorio. `.env` y `data/` en `.gitignore`.
- `.gitattributes` con `*.keras filter=lfs diff=lfs merge=lfs -text`.
- `README.md` mínimo con el front matter de Hugging Face Spaces (`sdk: gradio`, `app_file: app.py`,
  `sdk_version` = versión de Gradio instalada). El README final lo redactaré yo.

# CALIDAD Y VERIFICACIÓN
- Tests con pytest: (a) el preprocesado reproduce la predicción esperada sobre las imágenes de
  `modelo/ejemplos/`; (b) las etiquetas cubren las 38 clases; (c) lógica del umbral;
  (d) rechazo de entradas inválidas; (e) el acceso a administración falla sin contraseña correcta;
  (f) el CSV exportado neutraliza fórmulas.
- Ejecuta los tests y arranca la app localmente antes de dar el trabajo por terminado.

# FORMA DE TRABAJO
1. Primero presenta un plan breve (estructura, decisiones, riesgos) y espera mi aprobación.
​2. Implementa, ejecuta los tests y reporta resultados reales, no supuestos.
3. Señala cualquier desviación de este documento y cualquier decisión que hayas tomado por tu cuenta.

