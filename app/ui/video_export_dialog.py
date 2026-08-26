"""Dialog export video dengan subtitle: mode Burn-in (hardsub) atau Sisip Track (softsub)."""
import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core.video_export import VideoExporter, VideoExportCancelled
from ..core import video_utils
from ..utils.constants import (
    TARGET_LANGUAGES, LANGUAGES, COLOR_SECONDARY, COLOR_SECONDARY_HOVER,
    COLOR_DANGER, COLOR_DANGER_HOVER,
)


class VideoExportDialog(ctk.CTkToplevel):
    def __init__(self, master, doc, config_manager, subtitle_style=None):
        super().__init__(master)
        self.doc = doc
        self.config_manager = config_manager
        self.subtitle_style = subtitle_style
        self.exporter = VideoExporter()
        self.running = False

        self.title("Export Video dengan Subtitle - MaxSubtitle")
        self.geometry("560x620")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self.after(50, self._center_on_parent)

    def _center_on_parent(self):
        self.update_idletasks()
        try:
            px, py = self.master.winfo_rootx(), self.master.winfo_rooty()
            pw, ph = self.master.winfo_width(), self.master.winfo_height()
            w, h = 560, 620
            x, y = px + (pw - w) // 2, py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    # -------------------------------------------------------------- build
    def _build(self):
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=4)
        pad = {"padx": 20, "pady": (12, 4)}

        has_translated = any(l.translated_text for l in self.doc.lines)

        # --- mode ---
        ctk.CTkLabel(container, text="Mode Export",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.mode_var = ctk.StringVar(value="burnin")
        mode_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_frame.pack(anchor="w", padx=20, fill="x")
        ctk.CTkRadioButton(mode_frame, text="Burn-in (Hardsub) - subtitle dibakar permanen ke video",
                            variable=self.mode_var, value="burnin",
                            command=self._on_mode_change).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(mode_frame, text="Sisip Track (Softsub) - bisa on/off di pemutar video",
                            variable=self.mode_var, value="embed",
                            command=self._on_mode_change).pack(anchor="w", pady=2)

        # --- panel burn-in ---
        self.burnin_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(self.burnin_frame, text="Sumber Teks",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        text_source_labels = ["Terjemahan", "Teks Asli", "Dwibahasa (Asli + Terjemahan)"]
        self.text_source_menu = ctk.CTkOptionMenu(self.burnin_frame, values=text_source_labels, width=300)
        self.text_source_menu.set(text_source_labels[0] if has_translated else "Teks Asli")
        self.text_source_menu.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(self.burnin_frame, text="Kualitas",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        quality_labels = ["Cepat (file lebih besar)", "Sedang - rekomendasi", "Tinggi (proses lebih lama)"]
        self.quality_menu = ctk.CTkOptionMenu(self.burnin_frame, values=quality_labels, width=300)
        self.quality_menu.set(quality_labels[1])
        self.quality_menu.pack(anchor="w", pady=(0, 4))

        style_row = ctk.CTkFrame(self.burnin_frame, fg_color="transparent")
        style_row.pack(anchor="w", pady=(6, 2), fill="x")
        ctk.CTkButton(style_row, text="Gaya Subtitle (Font/Warna/Posisi)...", width=280,
                      command=self._open_style_dialog).pack(side="left")

        ctk.CTkLabel(self.burnin_frame,
                     text="Video akan di-render ulang sepenuhnya - bisa memakan waktu\n"
                          "cukup lama tergantung durasi video & kualitas dipilih.",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     justify="left").pack(anchor="w", pady=(4, 8))

        # --- panel embed ---
        self.embed_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(self.embed_frame, text="Track yang Disertakan",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        self.include_original_var = ctk.BooleanVar(value=True)
        self.include_translated_var = ctk.BooleanVar(value=has_translated)
        ctk.CTkCheckBox(self.embed_frame, text="Sertakan track Teks Asli",
                         variable=self.include_original_var).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(self.embed_frame, text="Sertakan track Terjemahan",
                         variable=self.include_translated_var,
                         state="normal" if has_translated else "disabled").pack(anchor="w", pady=2)

        ctk.CTkLabel(self.embed_frame, text="Format Output",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        format_labels = ["MKV - direkomendasikan (semua fitur didukung)", "MP4 (kompatibilitas lebih luas)"]
        self.format_menu = ctk.CTkOptionMenu(self.embed_frame, values=format_labels, width=380)
        self.format_menu.set(format_labels[0])
        self.format_menu.pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(self.embed_frame,
                     text="Proses cepat (video/audio tidak di-render ulang). Subtitle bisa\n"
                          "dinyalakan/dimatikan atau diganti bahasanya langsung di pemutar video\n"
                          "yang mendukung (VLC, MPV, dll).",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     justify="left").pack(anchor="w", pady=(4, 8))

        # --- output path ---
        ctk.CTkLabel(container, text="Simpan Sebagai",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        path_row = ctk.CTkFrame(container, fg_color="transparent")
        path_row.pack(anchor="w", padx=20, fill="x")
        self.output_path_var = ctk.StringVar(value="")
        self.output_entry = ctk.CTkEntry(path_row, textvariable=self.output_path_var, width=340)
        self.output_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(path_row, text="Pilih...", width=80, command=self._pick_output_path).pack(side="left")

        # --- progress ---
        self.status_label = ctk.CTkLabel(container, text="", font=ctk.CTkFont(size=11),
                                          text_color=("gray40", "gray60"), wraplength=480, justify="left")
        self.status_label.pack(anchor="w", padx=20, pady=(16, 2), fill="x")
        self.progress_bar = ctk.CTkProgressBar(container)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 8))

        # --- buttons ---
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=12)
        self.start_btn = ctk.CTkButton(btn_row, text="Mulai Export", fg_color=COLOR_SECONDARY,
                                        hover_color=COLOR_SECONDARY_HOVER, command=self._start_export)
        self.start_btn.pack(side="left")
        self.cancel_btn = ctk.CTkButton(btn_row, text="Batal", fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
                                         command=self._cancel_export, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Tutup", width=90, fg_color="gray40", hover_color="gray30",
                      command=self._on_close).pack(side="right")

        self._on_mode_change()
        self._update_default_output_path()

    def _on_mode_change(self):
        if self.mode_var.get() == "burnin":
            self.embed_frame.pack_forget()
            self.burnin_frame.pack(anchor="w", padx=20, fill="x")
        else:
            self.burnin_frame.pack_forget()
            self.embed_frame.pack(anchor="w", padx=20, fill="x")
        self._update_default_output_path()

    def _update_default_output_path(self):
        if not self.doc.video_path:
            return
        base = os.path.splitext(os.path.basename(self.doc.video_path))[0]
        out_dir = os.path.dirname(self.doc.video_path)
        if self.mode_var.get() == "burnin":
            default_path = os.path.join(out_dir, f"{base}_subtitled.mp4")
        else:
            ext = ".mkv" if "MKV" in self.format_menu.get() else ".mp4"
            default_path = os.path.join(out_dir, f"{base}_subtitled{ext}")
        self.output_path_var.set(default_path)

    def _pick_output_path(self):
        if self.mode_var.get() == "burnin":
            ext, filetypes = ".mp4", [("MP4", "*.mp4")]
        else:
            is_mkv = "MKV" in self.format_menu.get()
            ext = ".mkv" if is_mkv else ".mp4"
            filetypes = [("MKV", "*.mkv")] if is_mkv else [("MP4", "*.mp4")]
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes,
                                             initialfile=os.path.basename(self.output_path_var.get()))
        if path:
            self.output_path_var.set(path)

    def _open_style_dialog(self):
        from .subtitle_style_dialog import SubtitleStyleDialog
        from ..core.subtitle_style import SubtitleStyle
        if self.subtitle_style is None:
            self.subtitle_style = SubtitleStyle()

        def on_change(style):
            self.subtitle_style = style
            # kalau video panel jendela utama masih menampilkan video yang sama,
            # ikutkan preview live-nya juga supaya user langsung lihat hasilnya
            try:
                self.master.video_panel.set_subtitle_style(style)
            except Exception:
                pass

        SubtitleStyleDialog(self, self.subtitle_style, on_change=on_change)

    # ----------------------------------------------------------------- run
    def _start_export(self):
        if self.running:
            return
        if not self.doc.video_path:
            messagebox.showwarning("Tidak ada video", "Fitur ini butuh file video asli "
                                    "(bukan mode audio-saja).", parent=self)
            return
        if not self.doc.lines:
            messagebox.showwarning("Belum ada subtitle", "Belum ada baris subtitle untuk diexport.",
                                    parent=self)
            return
        if not video_utils.check_ffmpeg_available():
            messagebox.showerror("ffmpeg tidak ditemukan", "ffmpeg dibutuhkan untuk export video.",
                                  parent=self)
            return
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showwarning("Lokasi belum dipilih", "Pilih lokasi simpan file terlebih dahulu.",
                                    parent=self)
            return

        mode = self.mode_var.get()
        if mode == "embed":
            if not self.include_original_var.get() and not self.include_translated_var.get():
                messagebox.showwarning("Pilih minimal satu track",
                                        "Centang minimal salah satu: track Asli atau Terjemahan.",
                                        parent=self)
                return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Memulai...")

        lines = list(self.doc.lines)
        video_path = self.doc.video_path

        if mode == "burnin":
            source_choice = self.text_source_menu.get()
            use_translated = source_choice.startswith("Terjemahan")
            bilingual = source_choice.startswith("Dwibahasa")
            quality_map = {"Cepat": "cepat", "Sedang": "sedang", "Tinggi": "tinggi"}
            quality = next((v for k, v in quality_map.items()
                             if self.quality_menu.get().startswith(k)), "sedang")

            def task():
                try:
                    self.exporter.export_burned_in(
                        video_path, lines, output_path,
                        use_translated=use_translated, bilingual=bilingual, quality=quality,
                        style=self.subtitle_style,
                        progress_callback=lambda p, m: self.after(0, self._on_progress, p, m),
                    )
                    self.after(0, self._on_finished, None)
                except VideoExportCancelled:
                    self.after(0, self._on_finished, "Dibatalkan")
                except Exception as exc:
                    self.after(0, self._on_finished, str(exc))
        else:
            source_lang = self.doc.source_language or "auto"
            target_lang = self.config_manager.get("target_language", "id")

            def task():
                try:
                    self.exporter.export_embedded(
                        video_path, lines, output_path,
                        include_original=self.include_original_var.get(),
                        include_translated=self.include_translated_var.get(),
                        source_lang=source_lang, target_lang=target_lang,
                        progress_callback=lambda p, m: self.after(0, self._on_progress, p, m),
                    )
                    self.after(0, self._on_finished, None)
                except VideoExportCancelled:
                    self.after(0, self._on_finished, "Dibatalkan")
                except Exception as exc:
                    self.after(0, self._on_finished, str(exc))

        threading.Thread(target=task, daemon=True).start()

    def _on_progress(self, pct, msg):
        self.progress_bar.set(max(0.0, min(1.0, pct / 100.0)))
        self.status_label.configure(text=msg)

    def _on_finished(self, error):
        self.running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        if error is None:
            self.progress_bar.set(1.0)
            self.status_label.configure(text="Selesai!")
            messagebox.showinfo("Selesai", f"Video berhasil disimpan:\n{self.output_path_var.get()}",
                                 parent=self)
        elif error == "Dibatalkan":
            self.status_label.configure(text="Dibatalkan.")
        else:
            self.status_label.configure(text="Gagal.")
            messagebox.showerror("Export gagal", error, parent=self)

    def _cancel_export(self):
        self.exporter.cancel()
        self.status_label.configure(text="Membatalkan...")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Proses berjalan",
                                        "Export masih berjalan. Batalkan dan tutup?", parent=self):
                return
            self.exporter.cancel()
        self.destroy()
