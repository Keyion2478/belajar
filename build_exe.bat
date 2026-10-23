@echo off
title Membangun EXE AHA DRIVE
echo ========================================================
echo Memulai build Standalone EXE menggunakan PyInstaller...
echo ========================================================
cd /d "%~dp0"
pyinstaller --clean AhaDrive.spec
if errorlevel 1 (
    echo.
    echo Gagal melakukan build EXE!
    pause
    exit /b 1
)
echo.
echo ========================================================
echo SELESAI! File Standalone EXE tersimpan di:
echo dist\AHA DRIVE.exe
echo ========================================================
pause
