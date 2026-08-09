"""Model data subtitle: SubtitleLine (satu baris) & SubtitleDocument (koleksi baris)."""
from dataclasses import dataclass
from typing import List, Optional
import re


def ms_to_srt_time(ms: int) -> str:
    """00:00:00,000"""
    if ms < 0:
        ms = 0
    ms = int(ms)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, millis = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def ms_to_vtt_time(ms: int) -> str:
    return ms_to_srt_time(ms).replace(",", ".")


def ms_to_short_time(ms: int) -> str:
    """mm:ss.ttt - ditampilkan di grid editor supaya ringkas."""
    if ms < 0:
        ms = 0
    ms = int(ms)
    minutes, ms = divmod(ms, 60000)
    seconds, millis = divmod(ms, 1000)
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


_TIME_RE = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})")
_SHORT_TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2})[:.](\d{2})(?:[.,](\d{1,3}))?$")


def srt_time_to_ms(time_str: str) -> int:
    time_str = time_str.strip()
    match = _TIME_RE.search(time_str)
    if not match:
        return 0
    h, m, s, ms = match.groups()
    millis = int(ms.ljust(3, "0")[:3])
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + millis


def parse_flexible_time(time_str: str) -> Optional[int]:
    """Parse input manual dari kotak edit: terima '00:00:01,000',
    '00:01.500', '1:30', dsb. Kembalikan None kalau tidak valid."""
    time_str = time_str.strip()
    if not time_str:
        return None
    if _TIME_RE.search(time_str):
        return srt_time_to_ms(time_str)
    match = _SHORT_TIME_RE.match(time_str)
    if match:
        h, m, s, ms = match.groups()
        h = int(h) if h else 0
        millis = int(ms.ljust(3, "0")[:3]) if ms else 0
        return h * 3600000 + int(m) * 60000 + int(s) * 1000 + millis
    if time_str.replace(".", "", 1).isdigit():
        return int(float(time_str) * 1000)
    return None


@dataclass
class SubtitleLine:
    index: int
    start_ms: int
    end_ms: int
    text: str = ""
    translated_text: str = ""

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    @property
    def start_srt(self) -> str:
        return ms_to_srt_time(self.start_ms)

    @property
    def end_srt(self) -> str:
        return ms_to_srt_time(self.end_ms)

    def display_text(self, use_translated: bool = False, bilingual: bool = False) -> str:
        if bilingual and self.translated_text:
            return f"{self.text}\n{self.translated_text}"
        if use_translated and self.translated_text:
            return self.translated_text
        return self.text

    def clone(self) -> "SubtitleLine":
        return SubtitleLine(self.index, self.start_ms, self.end_ms, self.text, self.translated_text)


class SubtitleDocument:
    """Menyimpan seluruh baris subtitle + metadata proyek (video/audio terkait)."""

    def __init__(self):
        self.lines: List[SubtitleLine] = []
        self.video_path: Optional[str] = None
        self.audio_path: Optional[str] = None
        self.source_language: str = "auto"
        self.target_language: str = "id"
        self.dirty: bool = False

    def clear(self):
        self.lines = []
        self.dirty = False

    def renumber(self):
        for i, line in enumerate(self.lines, start=1):
            line.index = i

    def sort_by_time(self):
        self.lines.sort(key=lambda l: (l.start_ms, l.end_ms))
        self.renumber()

    def set_lines(self, lines: List[SubtitleLine]):
        self.lines = list(lines)
        self.sort_by_time()
        self.dirty = True

    def add_line(self, start_ms: int, end_ms: int, text: str = "",
                 translated_text: str = "") -> SubtitleLine:
        line = SubtitleLine(0, start_ms, max(end_ms, start_ms + 200), text, translated_text)
        self.lines.append(line)
        self.sort_by_time()
        self.dirty = True
        return line

    def remove_line(self, line: SubtitleLine):
        if line in self.lines:
            self.lines.remove(line)
            self.renumber()
            self.dirty = True

    def duplicate_line(self, line: SubtitleLine) -> Optional[SubtitleLine]:
        if line not in self.lines:
            return None
        idx = self.lines.index(line)
        new_line = line.clone()
        gap = min(500, max(50, line.duration_ms // 4))
        new_line.start_ms = line.end_ms + gap
        new_line.end_ms = new_line.start_ms + line.duration_ms
        self.lines.insert(idx + 1, new_line)
        self.renumber()
        self.dirty = True
        return new_line

    def merge_with_next(self, line: SubtitleLine) -> Optional[SubtitleLine]:
        if line not in self.lines:
            return None
        idx = self.lines.index(line)
        if idx + 1 >= len(self.lines):
            return None
        nxt = self.lines[idx + 1]
        line.text = f"{line.text} {nxt.text}".strip()
        line.translated_text = f"{line.translated_text} {nxt.translated_text}".strip()
        line.end_ms = nxt.end_ms
        self.lines.remove(nxt)
        self.renumber()
        self.dirty = True
        return line

    def split_line(self, line: SubtitleLine, split_at_char: int) -> Optional[SubtitleLine]:
        if line not in self.lines:
            return None
        text = line.text
        if split_at_char <= 0 or split_at_char >= len(text):
            return None
        idx = self.lines.index(line)
        mid_ms = line.start_ms + line.duration_ms // 2
        first_text, second_text = text[:split_at_char].strip(), text[split_at_char:].strip()
        new_line = SubtitleLine(0, mid_ms, line.end_ms, second_text)
        line.end_ms = max(mid_ms, line.start_ms + 100)
        line.text = first_text
        self.lines.insert(idx + 1, new_line)
        self.renumber()
        self.dirty = True
        return new_line

    def shift_all(self, offset_ms: int):
        for line in self.lines:
            line.start_ms = max(0, line.start_ms + offset_ms)
            line.end_ms = max(line.start_ms + 50, line.end_ms + offset_ms)
        self.dirty = True

    def scale_to_new_end(self, new_end_ms: int):
        """Regangkan/susutkan seluruh timing proporsional agar baris terakhir
        berakhir tepat di new_end_ms (berguna saat subtitle sedikit out-of-sync)."""
        if not self.lines:
            return
        old_start = self.lines[0].start_ms
        old_end = self.lines[-1].end_ms
        if old_end <= old_start:
            return
        factor = (new_end_ms - old_start) / (old_end - old_start)
        for line in self.lines:
            line.start_ms = old_start + int((line.start_ms - old_start) * factor)
            line.end_ms = old_start + int((line.end_ms - old_start) * factor)
        self.dirty = True

    def total_duration_ms(self) -> int:
        if not self.lines:
            return 0
        return max(l.end_ms for l in self.lines)

    def line_at_time(self, ms: int) -> Optional[SubtitleLine]:
        for line in self.lines:
            if line.start_ms <= ms <= line.end_ms:
                return line
        return None
