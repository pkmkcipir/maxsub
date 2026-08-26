"""Konstanta global aplikasi MaxSubtitle."""
import os
import sys

APP_NAME = "MaxSubtitle"
APP_VERSION = "2.0.0"
APP_AUTHOR = "iman.mn_"
COPYRIGHT_WATERMARK = "@copyright iman.mn_"
COPYRIGHT_FULL = "\u00a9 2025-2026 iman.mn_  \u2014  MaxSubtitle"
APP_ID = "com.imanmn.maxsubtitle"

# GUID tetap dipakai sebagai AppId Inno Setup (jangan diubah antar versi
# supaya update installer mengenali instalasi lama).
INNO_APP_GUID = "8F2A1B3C-4D5E-4F6A-9B8C-1D2E3F4A5B6C"

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_MODEL_LABELS = {
    "tiny": "Tiny (tercepat, akurasi rendah, ~75 MB)",
    "base": "Base (cepat, ~145 MB)",
    "small": "Small (seimbang, ~480 MB) - rekomendasi",
    "medium": "Medium (akurat, ~1.5 GB)",
    "large-v3": "Large-v3 (paling akurat, ~3 GB, butuh GPU)",
}

DEVICE_OPTIONS = ["auto", "cuda", "cpu"]
DEVICE_LABELS = {
    "auto": "Otomatis (pakai GPU jika tersedia)",
    "cuda": "Paksa GPU (NVIDIA CUDA)",
    "cpu": "Paksa CPU",
}

# Kode bahasa mengikuti standar yang dipahami faster-whisper & Google Translate.
LANGUAGES = {
    "auto": "Deteksi Otomatis",
    "en": "Inggris (English)",
    "id": "Indonesia",
    "ja": "Jepang",
    "ko": "Korea",
    "zh": "Mandarin",
    "es": "Spanyol",
    "fr": "Prancis",
    "de": "Jerman",
    "ar": "Arab",
    "ru": "Rusia",
    "pt": "Portugis",
    "hi": "Hindi",
    "th": "Thailand",
    "vi": "Vietnam",
    "ms": "Melayu",
    "tr": "Turki",
    "it": "Italia",
    "nl": "Belanda",
}
# Target translate tidak boleh "auto"
TARGET_LANGUAGES = {k: v for k, v in LANGUAGES.items() if k != "auto"}

SUPPORTED_VIDEO_EXT = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts", ".m4v", ".wmv"]
SUPPORTED_AUDIO_EXT = [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma"]
SUPPORTED_SUBTITLE_EXT = [".srt", ".vtt"]

THEME_OPTIONS = ["dark", "light", "system"]

# Palet warna profesional (deep corporate blue + teal) - dipakai untuk warna
# semantik tombol/indikator yang di-hardcode (di luar sistem tema CustomTkinter
# bawaan, mis. warna sukses/bahaya, atau widget ttk.Treeview yang punya sistem
# styling sendiri terpisah dari tema CTk). Selaras dengan assets/themes/professional.json.
COLOR_PRIMARY = "#1E3A8A"
COLOR_PRIMARY_HOVER = "#162B67"
COLOR_SECONDARY = "#0D9488"        # teal - aksi utama/status aktif/sukses
COLOR_SECONDARY_HOVER = "#096F66"
COLOR_DANGER = "#AA3333"           # batal/hapus/error
COLOR_DANGER_HOVER = "#882222"
COLOR_BG_DARK = "#111827"
COLOR_BG_DARK_SURFACE = "#1A2332"
COLOR_BG_LIGHT_SURFACE = "#FFFFFF"


def resource_path(relative_path: str) -> str:
    """Kembalikan path absolut ke resource, kompatibel dengan mode dev
    maupun saat sudah dibundel PyInstaller (sys._MEIPASS)."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_path, relative_path)


def is_frozen() -> bool:
    return hasattr(sys, "_MEIPASS")


def get_color_theme_path() -> str:
    """Path ke file tema warna profesional (deep blue + teal). Kalau file-nya
    entah kenapa hilang/rusak, fallback ke tema bawaan CustomTkinter "blue"
    supaya aplikasi tetap bisa jalan (tampilan kurang optimal, tapi tidak crash)."""
    path = resource_path(os.path.join("assets", "themes", "professional.json"))
    return path if os.path.exists(path) else "blue"
