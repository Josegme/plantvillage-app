# Cómo contribuir

¡Gracias por interesarte en el proyecto! Es un ejercicio de aprendizaje y cualquier mejora, grande o pequeña, es bienvenida: una corrección de un texto, una idea, un error encontrado o un cambio en el código.

## Ideas por donde empezar

- **Probarla con fotos tomadas en el campo** y contar qué pasa (abre un *issue* con el resultado y, si puedes compartirla, la foto).
- **Añadir más cultivos o enfermedades**, lo que implica entrenar de nuevo el modelo.
- **Traducir la interfaz** a otros idiomas.
- **Mejorar el modelo**: otras arquitecturas, aplicar los pesos de clase que ya se calculan, medir mejor la calibración de la confianza.
- **Mejorar la interfaz y la accesibilidad.**
- **Revisar los textos** de «Para qué sirve» y «Cómo se hizo» y avisar de lo que no se entienda.

## Cómo proponer un cambio

1. Haz un *fork* del repositorio y clónalo (necesitas [Git LFS](https://git-lfs.com), porque el modelo se guarda con esa extensión).
2. Crea el entorno e instala las dependencias de desarrollo (los pasos están en el [README](README.md)):

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

3. Crea una rama para tu cambio y haz los cambios.
4. Ejecuta las pruebas y comprueba que pasan:

   ```powershell
   .venv\Scripts\python.exe -m pytest -q
   ```

5. Abre un *pull request* explicando qué cambia y por qué. Si es un cambio de comportamiento, añade o ajusta pruebas.

¿No sabes por dónde empezar o no quieres programar? Abre un *issue* con tu idea o tu duda.

## Reglas del proyecto

- **No guardar imágenes de usuarios** ni datos personales: el historial guarda solo metadatos, y las copias temporales se borran. Cualquier cambio en esto necesita una justificación clara.
- **Las cifras de rendimiento se leen de `modelo/`**, no se escriben a mano. Los textos usan marcadores como `{{exactitud_test}}`.
- **El README y la página de `docs/` se generan.** Si cambias `contenido/*.md`, `scripts/generar_pagina.py` o las cifras del modelo, ejecuta `python scripts/generar_pagina.py` y sube también `README.md` y `docs/`. Las pruebas avisan si quedan desactualizados.
- **No modificar `modelo/plantvillage_mobilenetv2.keras` sin reentrenar y reevaluar**: los archivos de métricas, la matriz de confusión y los ejemplos deben salir del mismo entrenamiento.
- **La administración debe fallar cerrada** y cada función que devuelva datos de administración debe verificar la autorización en el servidor.
- Textos de la interfaz en español, en frases claras y sin jerga innecesaria.

## Seguridad

Si encuentras un problema de seguridad, abre un *issue* sin incluir datos sensibles ni pasos que permitan explotarlo, y describe el problema en general.
