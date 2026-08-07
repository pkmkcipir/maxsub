"""Transkripsi ucapan-ke-teks memakai faster-whisper.

Mendeteksi GPU NVIDIA otomatis; jika gagal (driver/CUDA tidak lengkap),
otomatis fallback ke CPU supaya aplikasi tetap bisa dipakai."""
from typing import Callable, List, Optional, Tuple

from .subtitle import SubtitleLine

ProgressCB = Optional[Callable[[float, str], None]]


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
        if self.device in ("cpu", "cuda"):
            return self.device
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def load_model(self, progress_callback: ProgressCB = None):
        from faster_whisper import WhisperModel

        device = self._resolve_device()
        compute_type = self.compute_type or ("float16" if device == "cuda" else "int8")
        key = (self.model_size, device, compute_type)
        if self._model is not None and self._loaded_key == key:
            return self._model

        if progress_callback:
            progress_callback(0, f"Memuat model Whisper '{self.model_size}' ({device})...")
        try:
            self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        except Exception as exc:
            if device == "cuda":
                # GPU gagal diinisialisasi (driver/CUDA/cuDNN tidak lengkap) -> fallback CPU.
                if progress_callback:
                    progress_callback(0, "GPU gagal diinisialisasi, beralih ke CPU...")
                device = "cpu"
                compute_type = "int8"
                self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            else:
                raise RuntimeError(
                    f"Gagal memuat model Whisper '{self.model_size}'. "
                    f"Periksa koneksi internet (model diunduh saat pertama kali dipakai). Detail: {exc}"
                )
        self._loaded_key = (self.model_size, device, compute_type)
        return self._model

    def transcribe(self, audio_path: str, language: Optional[str] = None,
                    progress_callback: ProgressCB = None) -> Tuple[List[SubtitleLine], str]:
        self.cancel_requested = False
        model = self.load_model(progress_callback)
        lang = None if (language is None or language == "auto") else language

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
