@echo off
title Compilar TikTok LIVE SongBot (.EXE)
echo ========================================================
echo   COMPILADOR AUTOMATICO A .EXE (PyInstaller)
echo ========================================================
echo.
cd /d "%~dp0\.."
python scripts/build_exe.py
echo.
pause
