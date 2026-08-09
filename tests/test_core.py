"""Unit test ringan untuk logika inti (tanpa GUI, tanpa internet, tanpa model AI).
Jalankan: python3 tests/test_core.py
"""
import os
import sys
import tempfile

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

print(f"\n== HASIL: {passed} lolos, {failed} gagal ==")
sys.exit(1 if failed else 0)
