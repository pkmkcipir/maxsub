"""Baca & tulis format subtitle: SRT, VTT, ASS/SSA, TXT."""
import re
from typing import List

from .subtitle import SubtitleLine, ms_to_srt_time, ms_to_vtt_time, srt_time_to_ms

SRT_TIME_LINE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)


def parse_srt(path: str) -> List[SubtitleLine]:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()
    blocks = re.split(r"\r?\n\r?\n+", content.strip())
    lines: List[SubtitleLine] = []
    for block in blocks:
        block_lines = [b for b in block.strip().splitlines()]
        if not block_lines:
            continue
        time_idx = 0
        if SRT_TIME_LINE.search(block_lines[0]) is None and len(block_lines) > 1:
            time_idx = 1
        if time_idx >= len(block_lines):
            continue
        match = SRT_TIME_LINE.search(block_lines[time_idx])
        if not match:
            continue
        start_ms = srt_time_to_ms(match.group(1))
        end_ms = srt_time_to_ms(match.group(2))
        text = "\n".join(block_lines[time_idx + 1:]).strip()
        text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)  # buang tag html sederhana <i>, <b>, dst.
        lines.append(SubtitleLine(len(lines) + 1, start_ms, end_ms, text))
    return lines


def write_srt(lines: List[SubtitleLine], path: str, use_translated: bool = False,
              bilingual: bool = False):
    with open(path, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines, start=1):
            text = line.display_text(use_translated, bilingual)
            f.write(f"{i}\n{ms_to_srt_time(line.start_ms)} --> {ms_to_srt_time(line.end_ms)}\n{text}\n\n")


def parse_vtt(path: str) -> List[SubtitleLine]:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()
    content = re.sub(r"^WEBVTT[^\n]*\n", "", content, count=1)
    content = re.sub(r"^NOTE[^\n]*\n(?:[^\n]*\n)*?\n", "", content, flags=re.MULTILINE)
    blocks = re.split(r"\r?\n\r?\n+", content.strip())
    lines: List[SubtitleLine] = []
    for block in blocks:
        block_lines = [b for b in block.strip().splitlines() if b.strip() != ""]
        if not block_lines:
            continue
        time_idx = 0 if "-->" in block_lines[0] else 1
        if time_idx >= len(block_lines) or "-->" not in block_lines[time_idx]:
            continue
        match = SRT_TIME_LINE.search(block_lines[time_idx])
        if not match:
            continue
        start_ms = srt_time_to_ms(match.group(1))
        end_ms = srt_time_to_ms(match.group(2))
        text = "\n".join(block_lines[time_idx + 1:]).strip()
        text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
        lines.append(SubtitleLine(len(lines) + 1, start_ms, end_ms, text))
    return lines


def write_vtt(lines: List[SubtitleLine], path: str, use_translated: bool = False,
              bilingual: bool = False):
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for line in lines:
            text = line.display_text(use_translated, bilingual)
            f.write(f"{ms_to_vtt_time(line.start_ms)} --> {ms_to_vtt_time(line.end_ms)}\n{text}\n\n")


def _ms_to_ass_time(ms: int) -> str:
    ms = max(0, int(ms))
    cs = ms // 10  # centiseconds
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(lines: List[SubtitleLine], path: str, use_translated: bool = False,
              bilingual: bool = False, video_width: int = 1920, video_height: int = 1080,
              font_name: str = "Arial", font_size: int = 42):
    header = (
        "[Script Info]\n"
        "Title: MaxSubtitle Export\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        f"PlayResX: {video_width}\n"
        f"PlayResY: {video_height}\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,2,1,2,10,10,25,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for line in lines:
            text = line.display_text(use_translated, bilingual).replace("\n", "\\N")
            f.write(
                f"Dialogue: 0,{_ms_to_ass_time(line.start_ms)},{_ms_to_ass_time(line.end_ms)},"
                f"Default,,0,0,0,,{text}\n"
            )


def write_txt(lines: List[SubtitleLine], path: str, use_translated: bool = False):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            text = line.translated_text if (use_translated and line.translated_text) else line.text
            if text:
                f.write(text + "\n")


def detect_format(path: str) -> str:
    return path.lower().rsplit(".", 1)[-1] if "." in path else ""


def load_subtitle_file(path: str) -> List[SubtitleLine]:
    fmt = detect_format(path)
    if fmt == "srt":
        return parse_srt(path)
    if fmt == "vtt":
        return parse_vtt(path)
    raise ValueError(f"Format subtitle '.{fmt}' belum didukung untuk dibuka (gunakan .srt atau .vtt).")


EXPORTERS = {
    "srt": write_srt,
    "vtt": write_vtt,
    "ass": write_ass,
    "txt": write_txt,
}
