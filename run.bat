@echo off
title AHA DRIVE • Astral Engine (Modern Web Desktop)
cd /d "%~dp0"
python main_web.py
if errorlevel 1 pause
