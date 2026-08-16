#!/usr/bin/env python3
"""MaxSubtitle - Penerjemah & Transkripsi Subtitle Video Otomatis
Copyright (c) iman.mn_

Menjalankan mode normal:
    python main.py

Menjalankan self-test (headless, tanpa mainloop, dipakai saat build/CI):
    python main.py --selftest
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--selftest" in sys.argv:
        from app.selftest import run_selftest
        sys.exit(run_selftest())

    import customtkinter as ctk
    from app.ui.main_window import MainWindow
    from app.utils.constants import get_color_theme_path

    ctk.set_default_color_theme(get_color_theme_path())

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
