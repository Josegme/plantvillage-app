## Cómo se hizo, paso a paso

Este proyecto es un ejercicio de aprendizaje de punta a punta: se **entrenó una red neuronal** en Google Colab para reconocer enfermedades en hojas y después se **empaquetó en esta aplicación** para poder usarla con una foto. Cada paso tiene dos partes: *qué se hizo* y *por qué*.

Las cifras de rendimiento de esta página se leen de los archivos de evaluación del modelo, no se escribieron a mano.

### 1. Conseguir los datos
**Qué se hizo.** Se usó **PlantVillage**, un conjunto público de fotos de hojas, en la versión publicada en Kaggle. Tiene 54.305 imágenes de 14 cultivos, repartidas en 38 clases (un cultivo más un estado: sana o con una enfermedad concreta). La descarga venía ya dividida en una parte de entrenamiento (43.444 imágenes) y otra de validación (10.861).

**Por qué.** Una red neuronal aprende de ejemplos. Para aprender a distinguir 38 clases necesita miles de fotos ya etiquetadas por especialistas, y armar ese conjunto desde cero sería inviable en un proyecto de estudio.

### 2. Mirar los datos antes de usarlos
**Qué se hizo.** Se contó cuántas imágenes hay por clase y se miraron fotos al azar. El reparto es muy desigual: la clase más pequeña (papa sana) tiene 121 imágenes de entrenamiento y la mayor (naranja con enverdecimiento de los cítricos), 4.405. Además, casi todas las fotos son de una sola hoja sobre un fondo liso.

**Por qué.** Los datos condicionan lo que el modelo aprende. Un reparto desigual hace que las clases con pocas fotos se aprendan peor, y las fotos «de estudio» anticipan que el modelo rendirá peor con fotos tomadas en el campo. Esa es la razón de las advertencias de la herramienta.

### 3. Separar los datos en tres partes
**Qué se hizo.** La parte de validación original se dividió por la mitad, respetando la proporción de cada clase: una mitad para **validación** (5.430 imágenes) y otra para **prueba** ({{n_test}} imágenes). Se fijó una semilla para poder repetir la división y se comprobó que ninguna imagen estuviera en dos partes a la vez. La parte de prueba se usó **una sola vez**, al final.

**Por qué.** Es como un examen: se estudia con unos ejercicios (entrenamiento), se hace una práctica para ajustar el método (validación) y se rinde el examen final con preguntas que nunca se vieron (prueba). Si el modelo viera las preguntas del examen mientras estudia, la nota no significaría nada.

### 4. Variar las fotos durante el entrenamiento
**Qué se hizo.** Se añadió una capa de «aumento de datos» que, solo mientras se entrena, voltea la imagen, la rota un poco, le hace zoom y cambia el contraste de forma aleatoria. También se calcularon pesos para compensar las clases pequeñas, pero en esta versión no se aplicaron en el entrenamiento.

**Por qué.** Así el modelo ve cada hoja de muchas formas y no memoriza las fotos exactas. En una foto real la hoja puede estar girada o tener otra luz.

### 5. Partir de un modelo que ya sabe mirar
**Qué se hizo.** En lugar de empezar de cero, se usó **MobileNetV2**, una red neuronal ya entrenada con millones de imágenes cotidianas (ImageNet). Se mantuvo congelada su parte principal (más de 2,2 millones de valores) y se le añadió al final una capa nueva con 38 salidas, una por clase, que sí se entrena (unos 48.000 valores). El modelo recibe fotos de 224 × 224 píxeles.

**Por qué.** Esta técnica se llama *transferencia de aprendizaje*. Una red que ya aprendió a reconocer bordes, texturas y formas no necesita aprenderlo otra vez: solo hay que enseñarle qué combinación de esas señales corresponde a cada enfermedad. Se entrena mucho más rápido y con menos datos, y MobileNetV2 es lo bastante ligera para funcionar en un ordenador sin tarjeta gráfica.

### 6. Primera fase de entrenamiento
**Qué se hizo.** Se entrenó solo la capa nueva, con pasos de aprendizaje grandes (0,001), durante un máximo de 8 pasadas completas por los datos (épocas). Se guardó el mejor punto según la validación y se detenía antes si dejaba de mejorar.

**Por qué.** Primero hay que enseñar a la capa nueva a interpretar lo que ya ve la red, sin tocar lo que esta ya sabe. Detener el entrenamiento a tiempo evita el sobreajuste: que el modelo aprenda tan bien los ejemplos que falle con los nuevos.

### 7. Ajuste fino
**Qué se hizo.** Se «descongelaron» las capas más profundas de MobileNetV2 (desde la capa 100) y se siguió entrenando con pasos 100 veces más pequeños (0,00001), hasta 12 épocas, con los mismos mecanismos de guardado y parada, y reduciendo el paso si el progreso se estancaba. Se compararon los resultados antes y después.

**Por qué.** Las capas profundas reconocen detalles más específicos, y ajustarlas a hojas mejora la precisión. Se hace con pasos muy pequeños para no «olvidar» lo aprendido de las millones de imágenes originales.

### 8. Buscar dónde falla
**Qué se hizo.** Se miró el rendimiento clase por clase, qué enfermedades se confundían entre sí y cuántas hojas enfermas se daban por sanas.

**Por qué.** Una cifra global esconde problemas. En una herramienta para plantas el error más costoso es dar por sana una hoja enferma, y por eso se midió aparte.

### 9. Evaluación final
**Qué se hizo.** Se probó el modelo final con las {{n_test}} imágenes de prueba que no se habían usado hasta entonces.

| Medida | Resultado | Qué significa |
|---|---|---|
| Exactitud | {{exactitud_test}} | De cada 100 hojas, cuántas clasificó bien. |
| F1 macro | {{f1_macro_test}} | Promedio del rendimiento de cada una de las 38 clases (combina aciertos y falsas alarmas), sin favorecer a las que tienen más fotos. |
| Exactitud top-3 | {{top3_test}} | Cuántas veces la respuesta correcta estuvo entre sus tres primeras opciones. |
| Hojas enfermas dadas por sanas | {{enfermas_sanas}} de {{enfermas_test}} | El error más costoso en esta aplicación. |

**Por qué.** Estas cifras tienen sentido porque el modelo nunca había visto esas imágenes. Aun así, son resultados con fotos de laboratorio: con fotos del campo se espera menos.

### 10. Empaquetar el modelo para la aplicación
**Qué se hizo.** Se guardó una versión ligera del modelo, solo para predecir, y se comprobó que, con el mismo preprocesado que usa esta aplicación, las predicciones coinciden con las de la evaluación en un conjunto de imágenes de prueba. Se eligieron ocho fotos de ejemplo entre las bien clasificadas.

**Por qué.** Un modelo puede rendir bien en el cuaderno y fallar en la aplicación si la imagen se prepara de otra manera. Comprobar que coinciden evita esa sorpresa.

### 11. Construir la aplicación
**Qué se hizo.** Se desarrolló en Python con Gradio. Antes de predecir, la aplicación valida la foto (formato, tamaño máximo de 5 MB y número de píxeles). Si la confianza queda por debajo del umbral, avisa de que el resultado no es concluyente. De cada consulta guarda solo datos de uso (fecha, resultado, confianza y una huella de la imagen), nunca la foto, y la pestaña de administración está protegida con contraseña.

**Por qué.** Un modelo solo es útil si cualquiera puede usarlo, y una herramienta que opina sobre plantas debe ser honesta sobre sus límites. Por eso los avisos, el umbral y el trato cuidadoso de las fotos forman parte del diseño y no son un añadido.

### Herramientas usadas
Python, TensorFlow y Keras para el modelo, Google Colab para entrenar, Kaggle como fuente de los datos, Gradio para la interfaz, Git y GitHub para el código y pytest para las pruebas automáticas.
