"""Transkripsi ucapan-ke-teks memakai faster-whisper.

Mendeteksi GPU NVIDIA otomatis; jika gagal (driver/CUDA/cuBLAS/cuDNN tidak
lengkap), otomatis fallback ke CPU supaya aplikasi tetap bisa dipakai.

PENTING: ctranslate2 baru benar-benar memuat library CUDA (mis. cublas64_12.dll)
saat inferensi PERTAMA dijalankan, bukan saat model dibuat/dimuat. Karena itu
seluruh alur (muat model + jalankan transkripsi) dibungkus try/except sekaligus,
bukan cuma bagian muat model saja - supaya fallback ke CPU benar-benar menjaring
error yang muncul telat seperti itu.

Modul ini juga otomatis mendaftarkan folder DLL milik paket pip
nvidia-cublas-cu12 / nvidia-cudnn-cu12 (kalau terpasang) lewat
os.add_dll_directory() di Windows - supaya user cukup `pip install
nvidia-cublas-cu12 nvidia-cudnn-cu12` tanpa perlu mengedit PATH sistem
secara manual."""
import os
from typing import Callable, List, Optional, Tuple

from .subtitle import SubtitleLine

ProgressCB = Optional[Callable[[float, str], None]]

_dll_dirs_registered = False


def _register_nvidia_pip_dll_dirs():
    """Kalau nvidia-cublas-cu12 / nvidia-cudnn-cu12 terpasang lewat pip (bukan
    CUDA Toolkit system-wide dari NVIDIA), DLL-nya ada di dalam site-packages,
    bukan di PATH Windows. Windows tidak lagi mencari DLL lewat PATH biasa
    untuk alasan keamanan sejak Python 3.8, jadi kita daftarkan foldernya
    secara eksplisit lewat os.add_dll_directory(). Aman dipanggil berkali-kali
    atau di sistem non-Windows (langsung keluar tanpa efek)."""
    global _dll_dirs_registered
    if _dll_dirs_registered or os.name != "nt":
        return
    _dll_dirs_registered = True
    import importlib.util
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_runtime"):
        try:
            spec = importlib.util.find_spec(pkg)
            if not spec or not spec.submodule_search_locations:
                continue
            base = list(spec.submodule_search_locations)[0]
            dll_dir = os.path.join(base, "bin")
            if os.path.isdir(dll_dir):
                os.add_dll_directory(dll_dir)
        except Exception:
            pass  # paket tidak terpasang atau format berbeda - lewati saja


class TranscribeCancelled(Exception):
    pass


class Transcriber:
    def __init__(self, model_size: str = "small", device: str = "auto",
                 compute_type: Optional[str] = None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._loaded_key = None
        self.cancel_requested = False

    def _resolve_device(self) -> str:
        _register_nvidia_pip_dll_dirs()
        if self.device in ("cpu", "cuda"):
            return self.device
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load_model_for(self, device: str, compute_type: str, progress_callback: ProgressCB):
        _register_nvidia_pip_dll_dirs()
        from faster_whisper import WhisperModel

        key = (self.model_size, device, compute_type)
        if self._model is not None and self._loaded_key == key:
            return self._model
        if progress_callback:
            progress_callback(0, f"Memuat model Whisper '{self.model_size}' ({device})...")
        model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        self._model = model
        self._loaded_key = key
        return model

    def load_model(self, progress_callback: ProgressCB = None):
        """Dipertahankan untuk kompatibilitas - memuat model di device hasil auto-detect.
        Catatan: ini TIDAK menjamin device tsb benar-benar bisa dipakai untuk inferensi
        (lihat docstring modul). Pemakaian utama tetap lewat transcribe()."""
        device = self._resolve_device()
        compute_type = self.compute_type or ("float16" if device == "cuda" else "int8")
        return self._load_model_for(device, compute_type, progress_callback)

    def _run_once(self, audio_path: str, lang: Optional[str], device: str,
                   compute_type: str, progress_callback: ProgressCB) -> Tuple[List[SubtitleLine], str]:
        model = self._load_model_for(device, compute_type, progress_callback)

        segments, info = model.transcribe(audio_path, language=lang, vad_filter=True,
                                           vad_parameters=dict(min_silence_duration_ms=400))

        lines: List[SubtitleLine] = []
        duration = getattr(info, "duration", 0) or 0
        detected_lang = getattr(info, "language", lang or "auto")

        for seg in segments:
            if self.cancel_requested:
                raise TranscribeCancelled()
            text = seg.text.strip()
            if not text:
                continue
            start_ms = int(seg.start * 1000)
            end_ms = int(seg.end * 1000)
            lines.append(SubtitleLine(len(lines) + 1, start_ms, end_ms, text))
            if progress_callback and duration:
                pct = min(99.0, (seg.end / duration) * 100)
                progress_callback(pct, f"Transkripsi... {_fmt_time(seg.end)} / {_fmt_time(duration)}")

        if progress_callback:
            progress_callback(100, f"Transkripsi selesai ({len(lines)} baris, bahasa: {detected_lang})")
        return lines, detected_lang

    def transcribe(self, audio_path: str, language: Optional[str] = None,
                    progress_callback: ProgressCB = None) -> Tuple[List[SubtitleLine], str]:
        self.cancel_requested = False
        lang = None if (language is None or language == "auto") else language
        device = self._resolve_device()
        compute_type = self.compute_type or ("float16" if device == "cuda" else "int8")

        try:
            return self._run_once(audio_path, lang, device, compute_type, progress_callback)
        except TranscribeCancelled:
            raise
        except Exception as exc:
            if device != "cuda":
                raise RuntimeError(
                    f"Transkripsi gagal di CPU. Detail: {exc}"
                ) from exc
            # GPU terdeteksi ada, tapi gagal dipakai untuk inferensi sungguhan -
            # library CUDA (cuBLAS/cuDNN) kemungkinan tidak lengkap di sistem ini.
            # Buang model yang gagal, coba ulang dari nol memakai CPU.
            if progress_callback:
                progress_callback(
                    0, f"GPU gagal dipakai ({exc}). Mencoba ulang dengan CPU...")
            self._model = None
            self._loaded_key = None
            try:
                return self._run_once(audio_path, lang, "cpu", "int8", progress_callback)
            except TranscribeCancelled:
                raise
            except Exception as exc2:
                raise RuntimeError(
                    "Transkripsi gagal baik di GPU maupun CPU.\n"
                    f"Error GPU: {exc}\nError CPU: {exc2}"
                ) from exc2

    def cancel(self):
        self.cancel_requested = True


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def gpu_available() -> bool:
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False
