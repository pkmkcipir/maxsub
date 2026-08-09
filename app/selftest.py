"""Self-test: bangun seluruh GUI tanpa masuk mainloop, untuk menangkap error
konstruksi widget (opsi tidak valid, layout salah, dsb) sebelum dirilis."""
import sys
import traceback


def run_selftest() -> int:
    try:
        import customtkinter as ctk
        from app.ui.main_window import MainWindow

        ctk.set_appearance_mode("dark")
        app = MainWindow()
        app.update_idletasks()
        app.update()

        # Sentuh beberapa alur ringan yang tidak butuh model AI/koneksi internet.
        from app.core.subtitle import SubtitleDocument
        doc = SubtitleDocument()
        doc.add_line(0, 2000, "Contoh baris satu", "Contoh translated")
        doc.add_line(2000, 4000, "Contoh baris dua")
        app.doc = doc
        app._on_lines_updated()
        app.update()
        app.editor_panel.select_line(doc.lines[0])
        app.update()

        app.update()
        app.destroy()
        print("SELFTEST OK")
        return 0
    except Exception as exc:
        traceback.print_exc()
        print(f"SELFTEST FAILED: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(run_selftest())
