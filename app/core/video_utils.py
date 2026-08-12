"""Wrapper ffmpeg/ffprobe: ekstrak audio dari video & ambil info media."""
import json
import os
import shutil
import subprocess

from ..utils.constants import resource_path


def _no_window_flags():
    """Cegah jendela konsol hitam muncul saat memanggil ffmpeg dari exe Windows."""
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def find_ffmpeg() -> str:
    bundled = resource_path(os.path.join("ffmpeg", "ffmpeg.exe"))
    if os.path.exists(bundled):
        return bundled
    path = shutil.which("ffmpeg")
    return path if path else "ffmpeg"


def find_ffprobe() -> str:
    bundled = resource_path(os.path.join("ffmpeg", "ffprobe.exe"))
    if os.path.exists(bundled):
        return bundled
    path = shutil.which("ffprobe")
    return path if path else "ffprobe"


def check_ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            [find_ffmpeg(), "-version"],
            capture_output=True,
            creationflags=_no_window_flags(),
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def extract_audio(input_path: str, output_path: str, sample_rate: int = 16000) -> str:
    """Ekstrak audio jadi WAV mono 16-bit PCM (format ideal untuk Whisper & waveform)."""
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg, "-y", "-i", input_path,
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-acodec", "pcm_s16le",
        output_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=_no_window_flags(), timeout=3600,
    )
    if result.returncode != 0:
        stderr_tail = (result.stderr or "")[-800:]
        raise RuntimeError(
            "Gagal mengekstrak audio. Pastikan ffmpeg terpasang & file tidak rusak.\n"
            f"Detail: {stderr_tail}"
        )
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Ekstraksi audio menghasilkan file kosong.")
    return output_path


def get_media_info(path: str) -> dict:
    info = {"duration": 0.0, "fps": 25.0, "width": 0, "height": 0, "has_audio": False, "has_video": False}
    ffprobe = find_ffprobe()
    cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, creationflags=_no_window_flags(), timeout=30,
        )
        if result.returncode != 0:
            return info
        data = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return info

    try:
        info["duration"] = float(data.get("format", {}).get("duration", 0) or 0)
    except (TypeError, ValueError):
        pass

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and not info["has_video"]:
            info["has_video"] = True
            info["width"] = stream.get("width", 0) or 0
            info["height"] = stream.get("height", 0) or 0
            rate = stream.get("r_frame_rate", "25/1")
            try:
                num, den = rate.split("/")
                info["fps"] = (float(num) / float(den)) if float(den) else 25.0
            except (ValueError, ZeroDivisionError):
                info["fps"] = 25.0
        elif codec_type == "audio":
            info["has_audio"] = True
    return info


def is_video_file(path: str) -> bool:
    from ..utils.constants import SUPPORTED_VIDEO_EXT
    return os.path.splitext(path)[1].lower() in SUPPORTED_VIDEO_EXT


def is_audio_file(path: str) -> bool:
    from ..utils.constants import SUPPORTED_AUDIO_EXT
    return os.path.splitext(path)[1].lower() in SUPPORTED_AUDIO_EXT
