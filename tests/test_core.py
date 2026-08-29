"""Unit test ringan untuk logika inti (tanpa GUI, tanpa internet, tanpa model AI).
Jalankan: python3 tests/test_core.py
"""
import os
import sys
import tempfile
import subprocess
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.subtitle import (
    SubtitleDocument, SubtitleLine, ms_to_srt_time, srt_time_to_ms,
    ms_to_vtt_time, parse_flexible_time,
)
from app.core import formats

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK  - {name}")
    else:
        failed += 1
        print(f"  GAGAL - {name}")


print("== Time conversion ==")
check("ms_to_srt_time 0", ms_to_srt_time(0) == "00:00:00,000")
check("ms_to_srt_time 3661500", ms_to_srt_time(3661500) == "01:01:01,500")
check("srt_time_to_ms roundtrip", srt_time_to_ms("01:02:03,456") == 3723456)
check("ms_to_vtt_time uses dot", ms_to_vtt_time(1500) == "00:00:01.500")
check("parse_flexible_time short", parse_flexible_time("01:30") == 90000)
check("parse_flexible_time full", parse_flexible_time("00:00:01,500") == 1500)
check("parse_flexible_time invalid", parse_flexible_time("abc") is None)

print("== SubtitleDocument ==")
doc = SubtitleDocument()
l1 = doc.add_line(1000, 2000, "Halo dunia")
l2 = doc.add_line(3000, 4000, "Baris kedua")
check("add_line count", len(doc.lines) == 2)
check("renumber sequential", doc.lines[0].index == 1 and doc.lines[1].index == 2)

dup = doc.duplicate_line(l1)
check("duplicate_line adds one", len(doc.lines) == 3)
check("duplicate_line text copied", dup.text == "Halo dunia")
doc.remove_line(dup)
check("remove_line back to two", len(doc.lines) == 2)

doc.shift_all(500)
check("shift_all moves start", doc.lines[0].start_ms == 1500)

l3 = doc.add_line(10000, 11000, "Baris ketiga")
merged = doc.merge_with_next(doc.lines[1])
check("merge_with_next reduces count", len(doc.lines) == 2)
check("merge_with_next combines text", "Baris kedua" in merged.text and "Baris ketiga" in merged.text)

long_line = doc.add_line(20000, 22000, "Kalimat ini punya dua bagian")
split_pos = long_line.text.index("punya")
new_line = doc.split_line(long_line, split_pos)
check("split_line adds a line", new_line is not None)
check("split_line first half text", long_line.text == "Kalimat ini")
check("split_line second half text", new_line.text.startswith("punya"))

print("== Format SRT roundtrip ==")
doc2 = SubtitleDocument()
doc2.add_line(0, 1500, "Ini baris pertama", "This is the first line")
doc2.add_line(2000, 4000, "Ini baris kedua\nDua baris", "Second line")
with tempfile.TemporaryDirectory() as tmp:
    srt_path = os.path.join(tmp, "out.srt")
    formats.write_srt(doc2.lines, srt_path)
    check("srt file created", os.path.exists(srt_path))
    reloaded = formats.parse_srt(srt_path)
    check("srt roundtrip count", len(reloaded) == 2)
    check("srt roundtrip text", reloaded[0].text == "Ini baris pertama")
    check("srt roundtrip multiline", "Dua baris" in reloaded[1].text)
    check("srt roundtrip timing", reloaded[1].start_ms == 2000 and reloaded[1].end_ms == 4000)

    vtt_path = os.path.join(tmp, "out.vtt")
    formats.write_vtt(doc2.lines, vtt_path)
    reloaded_vtt = formats.parse_vtt(vtt_path)
    check("vtt roundtrip count", len(reloaded_vtt) == 2)
    check("vtt roundtrip text", reloaded_vtt[0].text == "Ini baris pertama")

    bilingual_path = os.path.join(tmp, "bilingual.srt")
    formats.write_srt(doc2.lines, bilingual_path, bilingual=True)
    with open(bilingual_path, encoding="utf-8") as f:
        content = f.read()
    check("bilingual contains original", "Ini baris pertama" in content)
    check("bilingual contains translation", "This is the first line" in content)

    ass_path = os.path.join(tmp, "out.ass")
    formats.write_ass(doc2.lines, ass_path)
    with open(ass_path, encoding="utf-8") as f:
        ass_content = f.read()
    check("ass has Dialogue lines", ass_content.count("Dialogue:") == 2)
    check("ass has V4+ Styles header", "[V4+ Styles]" in ass_content)

    txt_path = os.path.join(tmp, "out.txt")
    formats.write_txt(doc2.lines, txt_path)
    with open(txt_path, encoding="utf-8") as f:
        txt_content = f.read()
    check("txt export plain text", "Ini baris pertama" in txt_content and "-->" not in txt_content)

print("== Waveform peaks (synthetic sine wave, no ffmpeg needed) ==")
try:
    import numpy as np
    import soundfile as sf
    from app.core.waveform import generate_peaks

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "tone.wav")
        sr = 16000
        t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
        tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        sf.write(wav_path, tone, sr)
        peaks, out_sr, total_samples = generate_peaks(wav_path, num_points=200)
        check("waveform peaks non-empty", len(peaks) > 0)
        check("waveform samplerate matches", out_sr == sr)
        check("waveform peaks normalized <=1", max(peaks) <= 1.0001)
        check("waveform total_samples matches duration", total_samples == int(sr * 2.0))
except ImportError as e:
    print(f"  DILEWATI - waveform test (dependency belum terpasang: {e})")

print("== Video export (butuh ffmpeg - dilewati otomatis kalau tidak ada) ==")
try:
    import shutil as _shutil
    from app.core import video_utils
    if not video_utils.check_ffmpeg_available():
        raise RuntimeError("ffmpeg tidak tersedia di sistem ini")

    from app.core.video_export import VideoExporter, VideoExportCancelled, _parse_time_to_seconds

    check("parse_time_to_seconds normal", abs(_parse_time_to_seconds("00:00:05.500000") - 5.5) < 0.01)
    check("parse_time_to_seconds N/A aman (tidak crash)", _parse_time_to_seconds("N/A") == 0.0)
    check("parse_time_to_seconds string kosong aman", _parse_time_to_seconds("") == 0.0)

    with tempfile.TemporaryDirectory() as tmp:
        test_video = os.path.join(tmp, "test.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", test_video, "-loglevel", "error",
        ], check=True, timeout=60)

        doc = SubtitleDocument()
        doc.add_line(200, 1500, "Baris asli", "Baris terjemahan")

        exporter = VideoExporter()
        progress_calls = []

        # -- burn-in --
        out_burned = os.path.join(tmp, "burned.mp4")
        exporter.export_burned_in(test_video, doc.lines, out_burned, use_translated=True,
                                   quality="cepat", progress_callback=lambda p, m: progress_calls.append(p))
        check("burn-in: file output dibuat", os.path.exists(out_burned))
        check("burn-in: ukuran file wajar", os.path.getsize(out_burned) > 5000)
        check("burn-in: progress callback terpanggil", len(progress_calls) > 0)
        check("burn-in: progress mencapai 100", progress_calls[-1] == 100)

        # -- embed --
        out_embed = os.path.join(tmp, "embed.mkv")
        exporter2 = VideoExporter()
        exporter2.export_embedded(test_video, doc.lines, out_embed,
                                   include_original=True, include_translated=True,
                                   source_lang="en", target_lang="id")
        check("embed: file output dibuat", os.path.exists(out_embed))
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", out_embed],
            capture_output=True, text=True,
        )
        streams = json.loads(probe.stdout)["streams"]
        sub_streams = [s for s in streams if s["codec_type"] == "subtitle"]
        check("embed: 2 track subtitle tersisip", len(sub_streams) == 2)
        check("embed: metadata bahasa benar", sub_streams[0]["tags"]["language"] == "eng"
              and sub_streams[1]["tags"]["language"] == "ind")

        # -- validasi: minimal satu track harus dipilih --
        try:
            exporter3 = VideoExporter()
            exporter3.export_embedded(test_video, doc.lines, os.path.join(tmp, "invalid.mkv"),
                                       include_original=False, include_translated=False)
            check("embed: menolak kalau tidak ada track dipilih", False)
        except ValueError:
            check("embed: menolak kalau tidak ada track dipilih", True)

except (RuntimeError, FileNotFoundError, subprocess.CalledProcessError) as e:
    print(f"  DILEWATI - video export test ({e})")
except ImportError as e:
    print(f"  DILEWATI - video export test (dependency belum terpasang: {e})")

print("== Gaya subtitle (subtitle_style.py) ==")
from app.core.subtitle_style import SubtitleStyle, hex_to_ass_color, render_subtitle_overlay

s = SubtitleStyle()
check("SubtitleStyle to_dict/from_dict roundtrip", SubtitleStyle.from_dict(s.to_dict()) == s)
check("SubtitleStyle.from_dict(None) fallback default", SubtitleStyle.from_dict(None) == SubtitleStyle())
check("SubtitleStyle.from_dict abaikan key asing",
      SubtitleStyle.from_dict({"font_size": 30, "key_aneh": 1}).font_size == 30)
check("SubtitleStyle.clone menghasilkan objek terpisah", s.clone() == s and s.clone() is not s)

check("hex_to_ass_color putih", hex_to_ass_color("#FFFFFF") == "&H00FFFFFF&")
check("hex_to_ass_color hitam", hex_to_ass_color("#000000") == "&H00000000&")
check("hex_to_ass_color merah jadi BGR", hex_to_ass_color("#FF0000") == "&H000000FF&")
check("hex_to_ass_color input rusak fallback putih", hex_to_ass_color("bukan-hex") == "&H00FFFFFF&")

try:
    from PIL import Image
    import numpy as np

    def _text_y_center(img):
        arr = np.array(img.convert("L"))
        bg = int(arr[0, 0])
        diff = np.abs(arr.astype(int) - bg)
        rows = np.where(diff.max(axis=1) > 30)[0]
        return float(rows.mean()) if len(rows) else None

    base = Image.new("RGB", (640, 360), (40, 80, 120))
    y_bottom = _text_y_center(render_subtitle_overlay(base, "x", SubtitleStyle(vertical_position=8), 640, 360))
    y_mid = _text_y_center(render_subtitle_overlay(base, "x", SubtitleStyle(vertical_position=45), 640, 360))
    y_top = _text_y_center(render_subtitle_overlay(base, "x", SubtitleStyle(vertical_position=85), 640, 360))
    check("posisi vertikal: bawah < tengah < atas (y makin kecil = makin ke atas)",
          y_bottom is not None and y_mid is not None and y_top is not None
          and y_bottom > y_mid > y_top)

    no_text = render_subtitle_overlay(base, "", SubtitleStyle(), 640, 360)
    check("render_subtitle_overlay teks kosong tidak crash & tidak menggambar apa pun",
          np.array_equal(np.array(no_text), np.array(base)))
except ImportError as e:
    print(f"  DILEWATI - render posisi test (numpy belum terpasang: {e})")

print("== Translator: deteksi respons gagal, retry, & fallback (tanpa internet) ==")
try:
    import deep_translator
    from app.core.translator import Translator, TranslateCancelled, _looks_like_failed_response

    _RAISE = object()
    _ERROR_PAGE = ("Error 500 (Server Error)!!1500.That's an error.There was an error. "
                   "Please try again later. That's all we know.")
    _MYMEMORY_QUOTA = "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY."

    class _FakeEngine:
        """Tiruan GoogleTranslator/MyMemoryTranslator, tanpa koneksi internet.
        `responses`: {teks_asli: [hasil_percobaan_1, hasil_percobaan_2, ...]}
        Item `_RAISE` mensimulasikan request yang gagal (exception)."""

        def __init__(self, responses, **kwargs):
            self.responses = responses
            self._calls = {}

        def translate(self, text):
            n = self._calls.get(text, 0)
            self._calls[text] = n + 1
            seq = self.responses.get(text, [text])
            val = seq[min(n, len(seq) - 1)]
            if val is _RAISE:
                raise RuntimeError("simulasi gagal jaringan")
            return val

    def _run_with_fakes(google_responses, mymemory_responses, texts, target="en"):
        orig_g = deep_translator.GoogleTranslator
        orig_m = deep_translator.MyMemoryTranslator
        deep_translator.GoogleTranslator = lambda **kw: _FakeEngine(google_responses)
        deep_translator.MyMemoryTranslator = lambda **kw: _FakeEngine(mymemory_responses)
        try:
            tr = Translator(source="auto", target=target)
            out = tr.translate_batch(texts)
            return out, tr.failed_count
        finally:
            deep_translator.GoogleTranslator = orig_g
            deep_translator.MyMemoryTranslator = orig_m

    check("_looks_like_failed_response mendeteksi halaman error Google",
          _looks_like_failed_response(_ERROR_PAGE))
    check("_looks_like_failed_response mendeteksi pesan kuota MyMemory",
          _looks_like_failed_response(_MYMEMORY_QUOTA))
    check("_looks_like_failed_response tidak salah tangkap teks normal",
          not _looks_like_failed_response("Hallo, wie geht es dir?"))

    # Skenario bug asli: Google "sukses" (HTTP 200) tapi isinya halaman error.
    out, n_fail = _run_with_fakes(
        google_responses={"Hallo Welt": [_ERROR_PAGE] * 5},
        mymemory_responses={"Hallo Welt": ["Hello World"]},
        texts=["Hallo Welt"],
    )
    check("bug halaman-error-jadi-terjemahan: terdeteksi & fallback ke MyMemory", out == ["Hello World"])
    check("bug halaman-error-jadi-terjemahan: tidak ada baris gagal tercatat", n_fail == 0)

    # Semua mesin gagal total -> teks asli dipertahankan, bukan halaman error.
    out, n_fail = _run_with_fakes(
        google_responses={"Es ist schwer": [_ERROR_PAGE] * 5},
        mymemory_responses={"Es ist schwer": [_RAISE] * 5},
        texts=["Es ist schwer"],
    )
    check("semua mesin gagal: teks asli dipertahankan (bukan halaman error)", out == ["Es ist schwer"])
    check("semua mesin gagal: failed_count tercatat 1", n_fail == 1)

    # Satu video, beberapa baris berbeda bahasa - tiap baris independen.
    texts = ["Guten Tag", "Bonjour le monde", "Hola amigo"]
    out, n_fail = _run_with_fakes(
        google_responses={
            "Guten Tag": ["Good day"],
            "Bonjour le monde": [_ERROR_PAGE, "Hello world"],
            "Hola amigo": [_ERROR_PAGE] * 5,
        },
        mymemory_responses={"Hola amigo": ["Hello friend"]},
        texts=texts,
    )
    check("baris multi-bahasa dlm 1 video diterjemahkan benar & independen",
          out == ["Good day", "Hello world", "Hello friend"])

    # Pembatalan di tengah proses harus tetap dihormati.
    class _CancelAfterFirst(_FakeEngine):
        def __init__(self, responses, translator_ref, **kwargs):
            super().__init__(responses)
            self._tr = translator_ref

        def translate(self, text):
            if text == "a":
                self._tr.cancel_requested = True
            return super().translate(text)

    tr = Translator(source="auto", target="en")
    orig_g, orig_m = deep_translator.GoogleTranslator, deep_translator.MyMemoryTranslator
    deep_translator.GoogleTranslator = lambda **kw: _CancelAfterFirst({}, tr)
    deep_translator.MyMemoryTranslator = lambda **kw: _CancelAfterFirst({}, tr)
    try:
        cancelled = False
        try:
            tr.translate_batch(["a", "b", "c"])
        except TranslateCancelled:
            cancelled = True
        check("cancel() di tengah proses menghentikan sisa baris", cancelled)
    finally:
        deep_translator.GoogleTranslator, deep_translator.MyMemoryTranslator = orig_g, orig_m

    # Target "zh" (Mandarin) dulu langsung meledak saat membuat GoogleTranslator
    # karena Google cuma kenal "zh-CN"/"zh-TW", bukan "zh" polos.
    tr_zh = Translator(source="auto", target="zh")
    engines_zh = tr_zh._build_engines()
    check("target bahasa 'zh' (Mandarin) tidak lagi gagal saat membuat mesin terjemahan",
          any(name == "Google Translate" for name, _ in engines_zh))

except ImportError as e:
    print(f"  DILEWATI - translator test (dependency belum terpasang: {e})")

print("== Translator: LibreTranslate lokal (opsional, tanpa limit) ==")
try:
    import deep_translator
    from app.core.translator import Translator

    # Nonaktif (default) -> perilaku persis spt sebelum fitur ini ada.
    tr_off = Translator(source="auto", target="id")
    names_off = [n for n, _ in tr_off._build_engines()]
    check("LibreTranslate nonaktif secara default (tak mengubah perilaku lama)",
          "LibreTranslate (lokal)" not in names_off and names_off[0] == "Google Translate")

    # Aktif + bahasa didukung (id) -> harus jadi prioritas PALING PERTAMA.
    tr_on = Translator(source="auto", target="id", use_libretranslate=True,
                        libretranslate_url="http://localhost:5000")  # sengaja tanpa trailing slash
    engines_on = tr_on._build_engines()
    names_on = [n for n, _ in engines_on]
    check("LibreTranslate aktif -> jadi mesin PERTAMA yang dicoba",
          names_on[:1] == ["LibreTranslate (lokal)"])
    check("URL tanpa trailing slash dinormalisasi otomatis",
          engines_on[0][1]._base_url == "http://localhost:5000/")

    # Aktif tapi bahasa TIDAK didukung LibreTranslate (mis. Thai) -> dilewati
    # otomatis, tetap ada Google/MyMemory sbg cadangan (tidak macet total).
    tr_th = Translator(source="auto", target="th", use_libretranslate=True)
    names_th = [n for n, _ in tr_th._build_engines()]
    check("bahasa yg tak didukung LibreTranslate (Thai) dilewati otomatis, fallback tetap ada",
          "LibreTranslate (lokal)" not in names_th and "Google Translate" in names_th)

    # End-to-end: LibreTranslate "menyala" (ditiru) & berhasil -> hasilnya
    # dipakai langsung, TIDAK PERNAH mencoba Google/MyMemory sama sekali.
    class _FakeLibre:
        def __init__(self, **kw):
            self.calls = 0

        def translate(self, text):
            self.calls += 1
            return f"[lokal] {text}"

    class _ShouldNotBeCalled:
        def __init__(self, **kw):
            pass

        def translate(self, text):
            raise AssertionError("Google seharusnya TIDAK dipanggil saat LibreTranslate berhasil")

    orig_libre = deep_translator.LibreTranslator
    orig_google = deep_translator.GoogleTranslator
    deep_translator.LibreTranslator = lambda **kw: _FakeLibre(**kw)
    deep_translator.GoogleTranslator = lambda **kw: _ShouldNotBeCalled(**kw)
    try:
        tr_e2e = Translator(source="auto", target="id", use_libretranslate=True)
        out_e2e = tr_e2e.translate_batch(["Hallo Welt"])
        check("LibreTranslate berhasil -> dipakai langsung tanpa pernah panggil Google",
              out_e2e == ["[lokal] Hallo Welt"])
    finally:
        deep_translator.LibreTranslator = orig_libre
        deep_translator.GoogleTranslator = orig_google

    # End-to-end REALISTIS: server LibreTranslate belum dinyalakan (dituju ke
    # port lokal yang memang kosong) - pakai KELAS ASLI (bukan tiruan) supaya
    # perilaku gagal-koneksinya sungguhan diuji, lalu harus otomatis lanjut
    # ke Google (ditiru) dengan cepat, bukan macet menunggu lama.
    class _FakeGoogleOK:
        def __init__(self, **kw):
            pass

        def translate(self, text):
            return {"Guten Tag": "Good day"}.get(text, text)

    orig_google2 = deep_translator.GoogleTranslator
    deep_translator.GoogleTranslator = lambda **kw: _FakeGoogleOK(**kw)
    try:
        t_start = time.time()
        tr_dead = Translator(source="auto", target="id", use_libretranslate=True,
                              libretranslate_url="http://127.0.0.1:59999")  # port kosong
        out_dead = tr_dead.translate_batch(["Guten Tag"])
        elapsed = time.time() - t_start
        check("server LibreTranslate belum nyala -> tetap dpt hasil benar via fallback Google",
              out_dead == ["Good day"])
        check("kegagalan koneksi LibreTranslate terdeteksi cepat (bukan hang lama)",
              elapsed < 15)
    finally:
        deep_translator.GoogleTranslator = orig_google2

except ImportError as e:
    print(f"  DILEWATI - libretranslate test (dependency belum terpasang: {e})")

print(f"\n== HASIL: {passed} lolos, {failed} gagal ==")
sys.exit(1 if failed else 0)
