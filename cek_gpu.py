#!/usr/bin/env python3
"""Diagnostik GPU untuk MaxSubtitle.

Jalankan script ini SEBELUM mencoba transkripsi video sungguhan, untuk cek
cepat apakah GPU NVIDIA Anda benar-benar siap dipakai atau tidak - tanpa
perlu menunggu proses transkripsi penuh cuma untuk ketemu error di tengah
jalan.

Cara pakai (dari folder MaxSubtitle, dengan venv aktif):
    python cek_gpu.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def line():
    print("-" * 60)


def main():
    print("=" * 60)
    print("  DIAGNOSTIK GPU - MaxSubtitle")
    print("=" * 60)
    print()

    # --- 1. Cek driver NVIDIA ---
    line()
    print("[1/4] Mengecek driver NVIDIA...")
    driver_ok = False
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            driver_ok = True
            print("[OK] Driver NVIDIA terpasang dan berjalan.")
            for l in result.stdout.splitlines():
                if "Driver Version" in l:
                    print("     " + l.strip())
                    break
        else:
            print("[GAGAL] Perintah 'nvidia-smi' ada tapi mengembalikan error.")
    except FileNotFoundError:
        print("[GAGAL] Perintah 'nvidia-smi' tidak ditemukan.")
        print("        Ini berarti driver NVIDIA belum terpasang, atau GPU Anda")
        print("        bukan GPU NVIDIA. Unduh driver di:")
        print("        https://www.nvidia.com/download/index.aspx")
    except Exception as exc:
        print(f"[GAGAL] Tidak bisa menjalankan nvidia-smi: {exc}")

    if not driver_ok:
        print()
        print("Berhenti di sini - tanpa driver NVIDIA, langkah selanjutnya pasti")
        print("gagal juga. Aplikasi akan tetap berjalan normal memakai CPU.")
        return 1

    # --- 2. Cek ctranslate2 mendeteksi device CUDA ---
    line()
    print("[2/4] Mengecek ctranslate2 mendeteksi GPU...")
    try:
        from app.core.transcriber import _register_nvidia_pip_dll_dirs
        _register_nvidia_pip_dll_dirs()
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        if count > 0:
            print(f"[OK] ctranslate2 mendeteksi {count} GPU CUDA.")
        else:
            print("[GAGAL] ctranslate2 terpasang tapi tidak mendeteksi GPU CUDA.")
            print("        Kemungkinan versi ctranslate2 tidak cocok, atau")
            print("        library CUDA dasar belum lengkap.")
            return 1
    except ImportError:
        print("[GAGAL] Modul ctranslate2 tidak ditemukan.")
        print("        Jalankan: pip install -r requirements.txt")
        return 1
    except Exception as exc:
        print(f"[GAGAL] Error saat cek ctranslate2: {exc}")
        return 1

    # --- 3. Cek library cuBLAS & cuDNN benar-benar bisa dimuat ---
    line()
    print("[3/4] Mengecek cuBLAS & cuDNN bisa dimuat (tes inferensi ringan)...")
    print("      (mengunduh model 'tiny' kalau belum ada di cache - butuh")
    print("       internet sebentar untuk percobaan pertama)")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cuda", compute_type="float16")

        import numpy as np
        silence = np.zeros(16000, dtype=np.float32)  # 1 detik audio hening
        segments, info = model.transcribe(silence, language="en")
        list(segments)  # paksa evaluasi supaya inferensi CUDA benar2 jalan

        print("[OK] cuBLAS & cuDNN berhasil dimuat, inferensi GPU berjalan normal!")
        print("     GPU Anda siap dipakai penuh oleh MaxSubtitle.")
    except Exception as exc:
        print(f"[GAGAL] {exc}")
        print()
        print("     GPU terdeteksi ADA, tapi library CUDA (cuBLAS/cuDNN) belum")
        print("     lengkap/cocok versinya. Lihat TUTORIAL_INSTALL_CUDA.md untuk")
        print("     langkah pemasangannya.")
        print()
        print("     Catatan: MaxSubtitle tetap akan berjalan normal pakai CPU")
        print("     sampai ini diperbaiki (otomatis fallback, tidak error).")
        return 1

    # --- 4. Ringkasan ---
    line()
    print("[4/4] Ringkasan")
    print()
    print("Semua pengecekan lolos - MaxSubtitle akan otomatis memakai GPU Anda")
    print("untuk transkripsi (jauh lebih cepat dari CPU).")
    return 0


if __name__ == "__main__":
    code = main()
    print()
    print("=" * 60)
    input("Tekan Enter untuk menutup...")
    sys.exit(code)
