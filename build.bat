@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   MaxSubtitle - Build Script
echo   Copyright iman.mn_
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di PATH.
    echo Install Python 3.10 - 3.12 dari https://www.python.org/downloads/
    echo Saat instalasi, centang "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/4] Membuat virtual environment (venv)...
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [2/4] Menginstall dependency (bisa beberapa menit di percobaan pertama)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal install dependency. Cek koneksi internet lalu coba lagi.
    pause
    exit /b 1
)

echo.
echo [3/4] Menjalankan self-test aplikasi...
python main.py --selftest
if errorlevel 1 (
    echo [ERROR] Self-test gagal. Aplikasi kemungkinan tidak akan berjalan dengan benar.
    echo Cek pesan error di atas.
    pause
    exit /b 1
)

echo.
echo [4/4] Building MaxSubtitle.exe dengan PyInstaller...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
python -m PyInstaller build.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] Build gagal. Cek pesan error di atas.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD SELESAI!
echo   Aplikasi ada di: dist\MaxSubtitle\MaxSubtitle.exe
echo.
echo   Langkah selanjutnya (opsional):
echo   Buka installer.iss dengan Inno Setup Compiler
echo   untuk membuat installer Windows (MaxSubtitle_Setup.exe)
echo ============================================
pause
