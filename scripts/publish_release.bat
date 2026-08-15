@echo off
title Publicar Nueva Release en GitHub
echo ========================================================
echo   PUBLICADOR AUTOMATICO DE RELEASES (.EXE + GITHUB)
echo ========================================================
echo.
cd /d "%~dp0\.."
python scripts/publish_release.py
echo.
pause
