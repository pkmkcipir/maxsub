"""Pemutar audio dengan dukungan seek, dipakai bersama VideoPanel untuk sinkronisasi.

Menggunakan sounddevice (bukan pygame/VLC) supaya tidak butuh dependency
eksternal tambahan saat dibundel jadi exe, dan seek-nya presisi (baca ulang
array numpy dari posisi sample yang tepat)."""
import threading
import time


class AudioPlayer:
    def __init__(self):
        self.data = None
        self.samplerate = None
        self._lock = threading.Lock()
        self._playing = False
        self._start_offset_ms = 0
        self._start_time = None
        self._available = True

    def load(self, path: str):
        import soundfile as sf
        self.data, self.samplerate = sf.read(path, dtype="float32", always_2d=False)
        with self._lock:
            self._playing = False
            self._start_offset_ms = 0
            self._start_time = None

    def play_from(self, ms: int):
        if self.data is None or self.samplerate is None:
            return
        try:
            import sounddevice as sd
            sd.stop()
            start_sample = int((ms / 1000.0) * self.samplerate)
            start_sample = max(0, min(start_sample, len(self.data)))
            sd.play(self.data[start_sample:], self.samplerate)
            self._available = True
        except Exception:
            # Tidak ada perangkat audio (mis. sandbox tanpa soundcard) -
            # jangan sampai membuat aplikasi crash, cukup nonaktifkan audio.
            self._available = False
        with self._lock:
            self._playing = True
            self._start_offset_ms = ms
            self._start_time = time.time()

    def pause(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        with self._lock:
            if self._playing and self._start_time is not None:
                elapsed = (time.time() - self._start_time) * 1000
                self._start_offset_ms = int(self._start_offset_ms + elapsed)
            self._playing = False
            self._start_time = None

    def stop(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        with self._lock:
            self._playing = False
            self._start_offset_ms = 0
            self._start_time = None

    def current_position_ms(self) -> int:
        with self._lock:
            if not self._playing or self._start_time is None:
                return self._start_offset_ms
            elapsed = (time.time() - self._start_time) * 1000
            return int(self._start_offset_ms + elapsed)

    def duration_ms(self) -> int:
        if self.data is None or self.samplerate is None:
            return 0
        return int(len(self.data) / self.samplerate * 1000)

    def is_playing(self) -> bool:
        with self._lock:
            return self._playing

    def has_finished(self) -> bool:
        return self.current_position_ms() >= self.duration_ms()
