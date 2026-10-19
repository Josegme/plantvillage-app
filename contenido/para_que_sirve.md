## Para qué sirve esta herramienta

### El problema
Las enfermedades de las plantas se notan primero en las hojas: manchas, cambios de color, bordes secos o un aspecto arrugado. Reconocerlas a tiempo ayuda a actuar antes de que se extiendan, pero no siempre hay un especialista a mano, y muchas enfermedades se parecen entre sí.

### Qué hace
Recibe la foto de una hoja y propone **las tres enfermedades más parecidas** entre las 38 que conoce (o indica que la hoja parece sana). Junto a cada propuesta muestra la **confianza del modelo**: un porcentaje que dice cuán segura está la red neuronal de esa respuesta.

Cubre 14 cultivos, entre ellos tomate, papa, maíz, uva, manzana y fresa.

### Cómo usarla
1. Sube una foto de una sola hoja, con buena luz y un fondo lo más liso posible, o saca una con la cámara. También puedes empezar con uno de los ejemplos.
2. Pulsa **Diagnosticar**.
3. Lee la hipótesis principal y las otras dos. Si el resultado sale como «no concluyente», prueba con otra foto.

### Quién puede aprovecharla
- **Estudiantes y docentes** que quieran ver cómo se aplica la inteligencia artificial a un problema real del campo.
- **Personas con huerta o jardín** que quieran una primera orientación para saber qué buscar o a quién consultar.
- **Quien quiera entender cómo funciona** un clasificador de imágenes: la pestaña «Cómo se hizo» cuenta el proceso paso a paso.

### Lo que puede y lo que no puede hacer
- **Puede** orientar sobre qué enfermedad se parece más a la que muestra la hoja. En las imágenes de prueba acertó el {{exactitud_test}} de las veces.
- **No sustituye** el diagnóstico de un profesional agronómico. Es una demostración.
- **Aprendió con fotos de laboratorio**: una hoja, fondo uniforme y buena luz. Con fotos tomadas en el campo, con varias hojas, sombras o fondos complicados, rinde peor.
- **No sabe decir «esto no es una hoja»**. Si le muestras una taza o una cara, igualmente propondrá una de las 38 opciones, casi seguro con poca confianza.
- **Puede equivocarse con enfermedades parecidas.** Las que más le cuestan son: {{debiles}}.
- **Una hoja enferma puede salir como sana**: en las imágenes de prueba pasó con {{enfermas_sanas}} de {{enfermas_test}} hojas enfermas. Un resultado «sana» no garantiza que la planta lo esté.

### Palabras que verás en la herramienta
- **Confianza del modelo:** el porcentaje que la red neuronal asigna a cada opción. No es una medida exacta de acierto: un valor alto no asegura que el diagnóstico sea correcto.
- **Umbral de confianza:** el mínimo que exige la herramienta para dar un resultado firme. Por defecto es 60 %. Puedes cambiarlo con el deslizador.
- **Resultado no concluyente:** la confianza de la mejor hipótesis quedó por debajo del umbral. La herramienta no da un diagnóstico firme, pero sigue mostrando las tres hipótesis.
- **Clase:** cada una de las 38 opciones posibles, formada por un cultivo y un estado (por ejemplo, «Tomate, tizón temprano» o «Manzana, sana»).
