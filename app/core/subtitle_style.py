"""Model gaya tampilan subtitle (font, ukuran, warna, posisi vertikal).

Dipakai sebagai satu sumber kebenaran (single source of truth) baik untuk
preview langsung di video_panel.py maupun untuk hasil burn-in export lewat
ffmpeg/libass (formats.write_ass) - supaya apa yang terlihat di preview
sama persis dengan hasil video akhir."""
import os
from dataclasses import dataclass, asdict

from PIL import ImageFont

from ..utils.constants import resource_path

# Font kurasi yang umum tersedia di Windows, plus Noto Sans yang sudah
# dibundel aplikasi (selalu ada apapun sistemnya). Key = nama yang tampil
# di dropdown & yang dikirim ke ffmpeg/ASS Fontname; value = kandidat nama
# file .ttf Windows (reguler, bold) untuk resolusi preview PIL.
FONT_CHOICES = {
    "Noto Sans (bawaan aplikasi)": None,  # None = pakai file bundel, lihat _load_font
    "Arial": ("arial.ttf", "arialbd.ttf"),
    "Calibri": ("calibri.ttf", "calibrib.ttf"),
    "Segoe UI": ("segoeui.ttf", "segoeuib.ttf"),
    "Tahoma": ("tahoma.ttf", "tahomabd.ttf"),
    "Verdana": ("verdana.ttf", "verdanab.ttf"),
    "Times New Roman": ("times.ttf", "timesbd.ttf"),
    "Georgia": ("georgia.ttf", "georgiab.ttf"),
    "Impact": ("impact.ttf", "impact.ttf"),
    "Comic Sans MS": ("comic.ttf", "comicbd.ttf"),
}
DEFAULT_FONT_NAME = "Noto Sans (bawaan aplikasi)"

WINDOWS_FONTS_DIR = r"C:\Windows\Fonts"


@dataclass
class SubtitleStyle:
    font_name: str = DEFAULT_FONT_NAME
    font_size: int = 42          # dalam pixel relatif resolusi video asli (satuan sama dgn ASS)
    bold: bool = True
    text_color: str = "#FFFFFF"  # putih
    outline_color: str = "#000000"  # hitam
    outline_width: int = 2
    vertical_position: int = 8   # 0=mepet bawah, 100=mepet atas (persen tinggi video)

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        if not d:
            return SubtitleStyle()
        valid_keys = SubtitleStyle.__dataclass_fields__.keys()
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return SubtitleStyle(**filtered)

    def clone(self):
        return SubtitleStyle(**self.to_dict())


def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> '&HAABBGGRR&' - format warna dipakai ASS/SSA (BGR, bukan RGB)."""
    hex_color = (hex_color or "#FFFFFF").lstrip("#")
    if len(hex_color) != 6:
        hex_color = "FFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{alpha:02X}{b}{g}{r}&"


_font_cache = {}


def load_preview_font(style: SubtitleStyle, size_px: int):
    """Muat font PIL untuk preview, sesuai family+bold di style. size_px sudah
    dalam skala tampilan (bukan resolusi video asli) - dihitung oleh caller."""
    cache_key = (style.font_name, style.bold, size_px)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font = None
    candidates = FONT_CHOICES.get(style.font_name)
    if candidates is None:
        # Noto Sans bawaan - variable font, pilih instance Bold/Regular
        bundled = resource_path(os.path.join("assets", "fonts", "NotoSans-Bold.ttf"))
        if os.path.exists(bundled):
            try:
                font = ImageFont.truetype(bundled, size_px)
                try:
                    names = font.get_variation_names()
                    target = b"Bold" if style.bold else b"Regular"
                    if target in names:
                        font.set_variation_by_name(target.decode())
                except Exception:
                    pass
            except Exception:
                font = None
    else:
        regular_file, bold_file = candidates
        filename = bold_file if style.bold else regular_file
        path = os.path.join(WINDOWS_FONTS_DIR, filename)
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size_px)
            except Exception:
                font = None

    if font is None:
        # fallback terakhir: coba font sistem umum lain, lalu default PIL
        for fallback_path in (
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ):
            if os.path.exists(fallback_path):
                try:
                    font = ImageFont.truetype(fallback_path, size_px)
                    break
                except Exception:
                    continue
    if font is None:
        font = ImageFont.load_default()

    _font_cache[cache_key] = font
    return font


def render_subtitle_overlay(img, text: str, style: SubtitleStyle,
                             video_width: int, video_height: int):
    """Gambar teks subtitle di atas gambar PIL `img` (yang bisa jadi sudah
    diskalakan untuk tampilan, ukurannya belum tentu sama dengan video_width/
    video_height asli) sesuai `style`. Mengembalikan Image baru (tidak
    mengubah `img` in-place). Dipakai bareng oleh preview live (video_panel)
    maupun preview statis (dialog gaya, quick merge)."""
    from PIL import ImageDraw
    if not text:
        return img
    img = img.copy()
    draw = ImageDraw.Draw(img)

    # skalakan ukuran font & posisi dari satuan "resolusi video asli" ke
    # satuan "gambar yang sedang digambar" (yang mungkin sudah di-resize)
    scale = img.height / max(1, video_height)
    font_size_px = max(8, int(style.font_size * scale))
    font = load_preview_font(style, font_size_px)

    lines = text.split("\n")[:2]
    heights, widths = [], []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=style.outline_width)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + max(0, len(lines) - 1) * 4

    bottom_margin_px = int((style.vertical_position / 100.0) * img.height)
    y = img.height - total_h - bottom_margin_px
    y = max(0, min(y, img.height - total_h))

    outline_color = style.outline_color if style.outline_width > 0 else None
    for i, line in enumerate(lines):
        w = widths[i]
        x = (img.width - w) // 2
        draw.text((x, y), line, font=font, fill=style.text_color,
                   stroke_width=style.outline_width, stroke_fill=outline_color)
        y += heights[i] + 4
    return img
