@echo off
rem Arranca la aplicacion de diagnostico de hojas y abre el navegador. Doble clic para usar.
cd /d "%~dp0"
title Diagnostico de hojas

if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno .venv en esta carpeta.
  echo Crealo una vez con:  py -3.13 -m venv .venv
  echo y luego:  .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

rem Si la app ya esta en marcha, solo abre el navegador.
powershell -NoProfile -Command "try { Invoke-WebRequest http://127.0.0.1:7860 -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
  echo La aplicacion ya estaba en marcha. Abriendo el navegador...
  if not defined PV_SIN_NAVEGADOR start "" http://127.0.0.1:7860
  exit /b 0
)

echo.
echo Pestana de administracion: escribe una clave para activarla, o pulsa Enter para dejarla desactivada.
set "ADMIN_PASSWORD="
set /p "ADMIN_PASSWORD=Clave de administracion (solo para esta sesion): "

echo.
echo Cargando el modelo (unos 20-30 segundos). El navegador se abrira solo cuando este listo.
echo Para cerrar la aplicacion, cierra esta ventana o pulsa Ctrl+C.
echo.

if not defined PV_SIN_NAVEGADOR (
  start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest http://127.0.0.1:7860 -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:7860'; break } catch { Start-Sleep -Seconds 2 } }"
)

".venv\Scripts\python.exe" app.py
echo.
echo La aplicacion se ha cerrado.
pause