# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller untuk MaxSubtitle.

Build dengan:  pyinstaller build.spec --noconfirm
Hasil ada di:  dist/MaxSubtitle/  (mode onedir - lebih cepat start & lebih
               gampang di-debug dibanding onefile, dan ini yang dibungkus
               installer.iss jadi installer Windows)
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [("assets", "assets")]
binaries = []
hiddenimports = []

# Paket-paket ini punya data file / binary native / import dinamis yang tidak
# selalu terdeteksi otomatis oleh PyInstaller, jadi kita kumpulkan eksplisit.
for pkg in ["faster_whisper", "ctranslate2", "customtkinter", "deep_translator", "tokenizers"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    "sounddevice",
    "soundfile",
    "cv2",
    "PIL._tkinter_finder",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter.test", "test", "unittest"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MaxSubtitle",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MaxSubtitle",
)
