# Despliegue en Hugging Face Spaces

El `README.md` del repositorio no lleva el bloque de configuración de Spaces porque GitHub lo mostraría como una tabla al principio de la página. Al desplegar, el `README.md` **del Space** debe empezar exactamente con este bloque (seguido del contenido que quieras):

```yaml
---
title: PlantVillage - Diagnóstico de hojas
sdk: gradio
sdk_version: 6.30.0
python_version: "3.13"
app_file: app.py
---
```

- `sdk_version` debe coincidir con la versión de Gradio de `requirements.txt` (`gradio==6.30.0`).
- `python_version: "3.13"` es el valor válido según la documentación de Spaces (versión 3.x o 3.x.x), pero no se ha probado en un despliegue real.
- Crear un Space de tipo Gradio exige un plan de pago (PRO) en Hugging Face.
- `ADMIN_PASSWORD` se define como **secreto** del Space (Settings → Variables and secrets), nunca en el repositorio.
- El `.keras` se sube con Git LFS (ya configurado en `.gitattributes`).
- En un Space gratuito el almacenamiento es efímero: el historial se pierde al reiniciar.
