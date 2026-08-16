"""Export video dengan subtitle: burn-in (hardsub, permanen di frame video)
atau sisip track (softsub, bisa on/off di pemutar video).

Progress ffmpeg di-parse lewat flag -progress (output key=value baris demi
baris ke stdout) - BUKAN dengan regex ke output status manusia yang biasa
(frame=... time=... di stderr, ditulis ulang pakai \\r). Cara -progress ini
jauh lebih stabil untuk diparse secara program (baris lengkap, machine
readable, tidak ada masalah buffering \\r vs \\n)."""
import os
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Callable, List, Optional

from .subtitle import SubtitleLine
from . import formats
from .video_utils import find_ffmpeg, get_media_info, _no_window_flags
from ..utils.constants import resource_path

ProgressCB = Optional[Callable[[float, str], None]]

# Kode bahasa internal (2 huruf) -> ISO 639-2 (3 huruf) untuk metadata track
# subtitle di file MKV/MP4, supaya pemutar video bisa menampilkan nama
# bahasa yang benar di menu pilihan subtitle.
LANG_ISO639_2 = {
    "auto": "und", "en": "eng", "id": "ind", "ja": "jpn", "ko": "kor",
    "zh": "chi", "es": "spa", "fr": "fre", "de": "ger", "ar": "ara",
    "ru": "rus", "pt": "por", "hi": "hin", "th": "tha", "vi": "vie",
    "ms": "may", "tr": "tur", "it": "ita", "nl": "dut",
}

QUALITY_PRESETS = {
    "cepat": ["-preset", "veryfast", "-crf", "23"],
    "sedang": ["-preset", "medium", "-crf", "20"],
    "tinggi": ["-preset", "slow", "-crf", "18"],
}


class VideoExportCancelled(Exception):
    pass


def _parse_time_to_seconds(time_str: str) -> float:
    """Parse 'HH:MM:SS.ffffff' dari output -progress jadi detik (float).
    Kembalikan 0.0 kalau formatnya tidak dikenal (mis. 'N/A' di baris awal),
    supaya progress bar tidak pernah crash gara-gara satu baris aneh."""
    try:
        h, m, s = time_str.strip().split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError):
        return 0.0


class VideoExporter:
    def __init__(self):
        self.cancel_requested = False

    def cancel(self):
        """Cukup set flag - proses berhenti & dipaksa mati (kalau perlu)
        di dalam loop polling _run_ffmpeg_with_progress sendiri, di thread
        yang sama yang menjalankan proses itu. Sengaja TIDAK memanggil
        terminate()/wait() dari sini (thread pemanggil, biasanya thread UI)
        supaya tidak ada dua thread yang bersamaan mengurus proses OS yang
        sama - pola itu bisa memicu keterlambatan/race, terutama di Windows."""
        self.cancel_requested = True

    # ------------------------------------------------------------- runner
    def _run_ffmpeg_with_progress(self, cmd: List[str], cwd: Optional[str],
                                   total_duration_s: float, progress_callback: ProgressCB,
                                   stage_label: str):
        self.cancel_requested = False
        process = subprocess.Popen(
            cmd, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, creationflags=_no_window_flags(),
        )

        stderr_lines: List[str] = []

        def read_stderr():
            try:
                for line in process.stderr:
                    stderr_lines.append(line)
            except Exception:
                pass

        def read_stdout():
            # Baca & urai baris progress di thread TERPISAH dari loop polling
            # pembatalan di bawah - supaya kecepatan ffmpeg menulis baris
            # progress (yang bisa saja ter-buffer OS/pipe dan telat sesaat,
            # terutama di Windows) tidak pernah menunda respons tombol Batal
            # sedikit pun. Dua kepentingan ini sekarang sepenuhnya lepas.
            try:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if line.startswith("out_time="):
                        current_s = _parse_time_to_seconds(line.split("=", 1)[1])
                        if progress_callback and total_duration_s > 0:
                            pct = min(99.0, (current_s / total_duration_s) * 100)
                            progress_callback(
                                pct, f"{stage_label}... {current_s:.0f}s / {total_duration_s:.0f}s")
            except Exception:
                pass

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread.start()
        stdout_thread.start()

        # Loop polling: cek TIAP 100ms apakah proses sudah selesai sendiri ATAU
        # user minta batal - sama sekali tidak menunggu baris output apa pun,
        # jadi responsif dalam waktu yang bisa dipastikan (bukan "kira-kira
        # secepat ffmpeg menulis progress"). Kalau dibatalkan: terminate()
        # dulu (di Windows ini setara kill langsung), beri sedikit jeda,
        # paksa kill() kalau ternyata masih hidup. SEMUA penantian proses
        # terjadi di sini saja, di satu thread ini - tidak ada thread lain
        # yang ikut memanggil wait()/kill() pada proses yang sama.
        while True:
            if process.poll() is not None:
                break
            if self.cancel_requested:
                try:
                    process.terminate()
                except Exception:
                    pass
                try:
                    process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except Exception:
                        pass
                    try:
                        process.wait(timeout=3)
                    except Exception:
                        pass
                break
            time.sleep(0.1)

        stdout_thread.join(timeout=3)
        stderr_thread.join(timeout=3)

        if self.cancel_requested:
            raise VideoExportCancelled()

        if process.returncode != 0:
            stderr_text = "".join(stderr_lines[-40:])
            raise RuntimeError(f"ffmpeg gagal (kode keluar {process.returncode}):\n{stderr_text}")

    # ------------------------------------------------------------ burn-in
    def export_burned_in(self, video_path: str, lines: List[SubtitleLine], output_path: str,
                          use_translated: bool = False, bilingual: bool = False,
                          quality: str = "sedang", style=None, progress_callback: ProgressCB = None):
        """Render ulang video dengan subtitle dibakar permanen ke frame (hardsub).
        style: SubtitleStyle opsional (font/ukuran/warna/posisi vertikal)."""
        info = get_media_info(video_path)
        duration = info.get("duration", 0) or 0
        width = info.get("width") or 1920
        height = info.get("height") or 1080
        preset_args = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["sedang"])

        with tempfile.TemporaryDirectory(prefix="maxsub_export_") as tmp_dir:
            # Ditulis dengan nama file polos (tanpa spasi/simbol) lalu ffmpeg
            # dijalankan dengan cwd=tmp_dir, supaya filter -vf cukup mereferensi
            # "subs.ass" tanpa perlu escaping path Windows (C:\... , titik dua,
            # spasi, dll - sumber bug klasik di filter ffmpeg kalau path lengkap
            # dimasukkan langsung ke string filter).
            sub_name = "subs.ass"
            formats.write_ass(lines, os.path.join(tmp_dir, sub_name),
                               use_translated=use_translated, bilingual=bilingual,
                               video_width=width, video_height=height, style=style)

            # Kalau style memakai font bawaan aplikasi (Noto Sans, belum tentu
            # ter-install di sistem), salin file font-nya ke tmp_dir juga dan
            # arahkan libass ke situ lewat opsi fontsdir (relatif ke cwd, jadi
            # tidak perlu escaping path Windows sama sekali - sama seperti trik
            # untuk subs.ass di atas).
            fontsdir_opt = ""
            from .subtitle_style import FONT_CHOICES
            if style is not None and FONT_CHOICES.get(style.font_name) is None:
                bundled_font = resource_path(os.path.join("assets", "fonts", "NotoSans-Bold.ttf"))
                if os.path.exists(bundled_font):
                    shutil.copy(bundled_font, os.path.join(tmp_dir, "NotoSans-Bold.ttf"))
                    fontsdir_opt = ":fontsdir=."

            base_cmd = [
                find_ffmpeg(), "-y", "-i", video_path,
                "-vf", f"ass={sub_name}{fontsdir_opt}",
                "-c:v", "libx264", *preset_args,
                "-progress", "pipe:1", "-nostats",
            ]

            # Coba dulu audio "copy" (cepat, tanpa kualitas berkurang). Kalau
            # gagal (codec audio sumber tidak didukung wadah output), otomatis
            # ulangi dengan audio di-encode ulang ke AAC yang kompatibel luas.
            try:
                cmd = base_cmd + ["-c:a", "copy", output_path]
                self._run_ffmpeg_with_progress(cmd, tmp_dir, duration, progress_callback,
                                                "Membakar subtitle ke video")
            except VideoExportCancelled:
                raise
            except RuntimeError:
                if progress_callback:
                    progress_callback(0, "Audio copy gagal, mencoba ulang dengan re-encode audio (AAC)...")
                cmd = base_cmd + ["-c:a", "aac", "-b:a", "192k", output_path]
                self._run_ffmpeg_with_progress(cmd, tmp_dir, duration, progress_callback,
                                                "Membakar subtitle ke video (audio AAC)")

        if progress_callback:
            progress_callback(100, "Export video (burn-in) selesai")

    # ------------------------------------------------------------- embed
    def export_embedded(self, video_path: str, lines: List[SubtitleLine], output_path: str,
                         include_original: bool = True, include_translated: bool = True,
                         source_lang: str = "auto", target_lang: str = "id",
                         original_title: str = "Asli", translated_title: str = "Terjemahan",
                         progress_callback: ProgressCB = None):
        """Sisipkan subtitle sebagai track terpisah (softsub) - cepat, tanpa
        render ulang video/audio, subtitle bisa dimatikan di pemutar video.

        original_title/translated_title bisa diisi nama bahasa (mis. "Indonesia")
        supaya lebih jelas dibaca di menu pemutar video, terutama saat cuma satu
        track yang disertakan (label "Asli" kurang cocok berdiri sendiri tanpa
        pasangan "Terjemahan")."""
        if not include_original and not include_translated:
            raise ValueError("Minimal satu track (asli/terjemahan) harus disertakan.")

        info = get_media_info(video_path)
        duration = info.get("duration", 0) or 0
        ext = os.path.splitext(output_path)[1].lower()
        sub_codec = "srt" if ext == ".mkv" else "mov_text"

        with tempfile.TemporaryDirectory(prefix="maxsub_export_") as tmp_dir:
            cmd = [find_ffmpeg(), "-y", "-i", video_path]
            track_specs = []  # (lang_code, judul)

            if include_original:
                name = "orig.srt"
                formats.write_srt(lines, os.path.join(tmp_dir, name), use_translated=False)
                cmd += ["-i", name]
                track_specs.append((source_lang, original_title))

            if include_translated:
                name = "trans.srt"
                formats.write_srt(lines, os.path.join(tmp_dir, name), use_translated=True)
                cmd += ["-i", name]
                track_specs.append((target_lang, translated_title))

            cmd += ["-map", "0"]
            for i in range(len(track_specs)):
                cmd += ["-map", str(i + 1)]
            cmd += ["-c", "copy", "-c:s", sub_codec]

            for i, (lang, title) in enumerate(track_specs):
                iso = LANG_ISO639_2.get(lang, "und")
                cmd += [f"-metadata:s:s:{i}", f"language={iso}",
                        f"-metadata:s:s:{i}", f"title={title}"]

            cmd += ["-progress", "pipe:1", "-nostats", output_path]

            try:
                self._run_ffmpeg_with_progress(cmd, tmp_dir, duration, progress_callback,
                                                "Menyisipkan track subtitle")
            except VideoExportCancelled:
                raise
            except RuntimeError as exc:
                hint = (" Coba ganti format output ke MKV (mendukung lebih banyak "
                        "codec tanpa perlu re-encode).") if ext != ".mkv" else ""
                raise RuntimeError(f"{exc}\n{hint}") from exc

        if progress_callback:
            progress_callback(100, "Export video (sisip track) selesai")
