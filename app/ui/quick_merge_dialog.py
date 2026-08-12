"""Dialog mandiri: gabungkan video + file subtitle yang sudah jadi jadi satu
video hasil (burn-in atau sisip track) - TANPA perlu buka proyek/editor penuh.

Cocok untuk kasus: video dan file SRT sudah ada duluan (bukan hasil
transkripsi/terjemahan AI di aplikasi ini, misal subtitle dari sumber lain),
tinggal digabung jadi satu file video. Memakai ulang mesin export yang sama
dengan VideoExportDialog (app/core/video_export.py), tapi berdiri sendiri -
tidak menyentuh SubtitleDocument milik jendela utama sama sekali."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from ..core import formats, video_utils
from ..core.video_export import VideoExporter, VideoExportCancelled
from ..core.subtitle import ms_to_srt_time
from ..core.subtitle_style import SubtitleStyle, render_subtitle_overlay
from ..utils.constants import LANGUAGES, SUPPORTED_VIDEO_EXT


class QuickMergeDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.video_path = None
        self.video_dims = (1920, 1080)
        self.subtitle_lines = []
        self.subtitle_style = SubtitleStyle()
        self._preview_frame_pil = None
        self._preview_photo = None
        self.exporter = VideoExporter()
        self.running = False

        self.title("Gabung Video + Subtitle - MaxSubtitle")
        self.geometry("560x760")
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
            w, h = 560, 760
            x, y = px + (pw - w) // 2, py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    # -------------------------------------------------------------- build
    def _build(self):
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=4)
        pad = {"padx": 20, "pady": (12, 4)}

        ctk.CTkLabel(
            container,
            text="Gabungkan video dengan file subtitle yang sudah jadi (SRT/VTT) "
                 "jadi satu file video - tanpa perlu buka proyek penuh.",
            font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
            wraplength=480, justify="left",
        ).pack(anchor="w", padx=20, pady=(14, 4))

        # --- 1. video ---
        ctk.CTkLabel(container, text="1. Pilih Video",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        video_row = ctk.CTkFrame(container, fg_color="transparent")
        video_row.pack(anchor="w", padx=20, fill="x")
        self.video_path_var = ctk.StringVar(value="")
        self.video_entry = ctk.CTkEntry(video_row, textvariable=self.video_path_var, width=340)
        self.video_entry.pack(side="left", padx=(0, 6))
        self.video_entry.configure(state="disabled")
        ctk.CTkButton(video_row, text="Pilih Video...", width=110,
                      command=self._pick_video).pack(side="left")
        self.video_info_label = ctk.CTkLabel(container, text="Belum ada video dipilih.",
                                              font=ctk.CTkFont(size=11),
                                              text_color=("gray40", "gray60"))
        self.video_info_label.pack(anchor="w", padx=20, pady=(2, 0))

        # --- 2. subtitle ---
        ctk.CTkLabel(container, text="2. Pilih Subtitle (SRT/VTT)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        sub_row = ctk.CTkFrame(container, fg_color="transparent")
        sub_row.pack(anchor="w", padx=20, fill="x")
        self.sub_path_var = ctk.StringVar(value="")
        self.sub_entry = ctk.CTkEntry(sub_row, textvariable=self.sub_path_var, width=340)
        self.sub_entry.pack(side="left", padx=(0, 6))
        self.sub_entry.configure(state="disabled")
        ctk.CTkButton(sub_row, text="Pilih Subtitle...", width=110,
                      command=self._pick_subtitle).pack(side="left")
        self.sub_info_label = ctk.CTkLabel(container, text="Belum ada subtitle dipilih.",
                                            font=ctk.CTkFont(size=11),
                                            text_color=("gray40", "gray60"))
        self.sub_info_label.pack(anchor="w", padx=20, pady=(2, 0))

        # --- 3. mode ---
        ctk.CTkLabel(container, text="3. Mode Gabung",
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

        self.burnin_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(self.burnin_frame, text="Kualitas",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        quality_labels = ["Cepat (file lebih besar)", "Sedang - rekomendasi", "Tinggi (proses lebih lama)"]
        self.quality_menu = ctk.CTkOptionMenu(self.burnin_frame, values=quality_labels, width=300)
        self.quality_menu.set(quality_labels[1])
        self.quality_menu.pack(anchor="w", pady=(0, 4))

        ctk.CTkButton(self.burnin_frame, text="Gaya Subtitle (Font/Warna/Posisi)...", width=280,
                      command=self._open_style_dialog).pack(anchor="w", pady=(6, 6))

        ctk.CTkLabel(self.burnin_frame, text="Preview", font=ctk.CTkFont(size=11),
                     text_color=("gray40", "gray60")).pack(anchor="w")
        # tk.Label biasa (bukan CTkLabel) supaya update PhotoImage mentah stabil,
        # sama seperti pola di video_panel.py - CTkLabel butuh CTkImage utk scaling
        # HighDPI yang benar, tapi utk preview per-perubahan-slider begini PIL
        # PhotoImage langsung lebih ringan & tanpa warning.
        preview_wrapper = ctk.CTkFrame(self.burnin_frame, fg_color="#101010", corner_radius=6,
                                        height=140)
        preview_wrapper.pack(anchor="w", fill="x", pady=(2, 8))
        preview_wrapper.pack_propagate(False)
        self.preview_label = tk.Label(
            preview_wrapper, text="Pilih video untuk melihat preview gaya subtitle",
            bg="#101010", fg="gray50")
        self.preview_label.pack(fill="both", expand=True)

        self.embed_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctk.CTkLabel(self.embed_frame, text="Format Output",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        format_labels = ["MKV - direkomendasikan (semua fitur didukung)", "MP4 (kompatibilitas lebih luas)"]
        self.format_menu = ctk.CTkOptionMenu(self.embed_frame, values=format_labels, width=380,
                                              command=lambda _v: self._update_default_output_path())
        self.format_menu.set(format_labels[0])
        self.format_menu.pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(self.embed_frame, text="Bahasa Subtitle (untuk metadata track)",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 2))
        self.lang_menu = ctk.CTkOptionMenu(self.embed_frame, values=list(LANGUAGES.values()), width=300)
        self.lang_menu.set(LANGUAGES["id"])
        self.lang_menu.pack(anchor="w", pady=(0, 4))

        # --- 4. output ---
        ctk.CTkLabel(container, text="4. Simpan Sebagai",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        out_row = ctk.CTkFrame(container, fg_color="transparent")
        out_row.pack(anchor="w", padx=20, fill="x")
        self.output_path_var = ctk.StringVar(value="")
        self.output_entry = ctk.CTkEntry(out_row, textvariable=self.output_path_var, width=340)
        self.output_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(out_row, text="Pilih...", width=80, command=self._pick_output_path).pack(side="left")

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
        self.start_btn = ctk.CTkButton(btn_row, text="Mulai Gabung", fg_color="#2fa572",
                                        hover_color="#227a54", command=self._start_merge)
        self.start_btn.pack(side="left")
        self.cancel_btn = ctk.CTkButton(btn_row, text="Batal", fg_color="#a33", hover_color="#822",
                                         command=self._cancel_merge, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Tutup", width=90, fg_color="gray40", hover_color="gray30",
                      command=self._on_close).pack(side="right")

        self._on_mode_change()

    def _on_mode_change(self):
        if self.mode_var.get() == "burnin":
            self.embed_frame.pack_forget()
            self.burnin_frame.pack(anchor="w", padx=20, fill="x")
        else:
            self.burnin_frame.pack_forget()
            self.embed_frame.pack(anchor="w", padx=20, fill="x")
        self._update_default_output_path()

    # ------------------------------------------------------------ pickers
    def _pick_video(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_VIDEO_EXT)
        path = filedialog.askopenfilename(title="Pilih video", parent=self,
                                           filetypes=[("Video", exts), ("Semua file", "*.*")])
        if not path:
            return
        if not video_utils.check_ffmpeg_available():
            messagebox.showerror("ffmpeg tidak ditemukan", "ffmpeg dibutuhkan untuk membaca video.",
                                  parent=self)
            return
        info = video_utils.get_media_info(path)
        if not info.get("has_video"):
            messagebox.showerror("Bukan video", "File yang dipilih tidak punya track video.", parent=self)
            return
        self.video_path = path
        self.video_dims = (info.get("width") or 1920, info.get("height") or 1080)
        self.video_path_var.set(path)
        self.video_entry.configure(state="normal")
        self.video_entry.xview_moveto(1.0)
        self.video_entry.configure(state="disabled")
        duration_txt = ms_to_srt_time(int(info.get("duration", 0) * 1000)).split(",")[0]
        audio_txt = "ada audio" if info.get("has_audio") else "TANPA audio"
        self.video_info_label.configure(
            text=f"Durasi {duration_txt}  \u00b7  {info.get('width')}x{info.get('height')}px  \u00b7  {audio_txt}")
        self._update_default_output_path()
        self._extract_preview_frame(path, info.get("duration", 0) or 0)

    def _pick_subtitle(self):
        path = filedialog.askopenfilename(
            title="Pilih file subtitle", parent=self,
            filetypes=[("Subtitle", "*.srt *.vtt"), ("Semua file", "*.*")])
        if not path:
            return
        try:
            lines = formats.load_subtitle_file(path)
        except Exception as exc:
            messagebox.showerror("Gagal membaca subtitle", str(exc), parent=self)
            return
        if not lines:
            messagebox.showwarning(
                "Subtitle kosong",
                "File ini berhasil dibuka tapi tidak ada baris subtitle yang bisa dibaca.",
                parent=self)
            return
        self.subtitle_lines = lines
        self.sub_path_var.set(path)
        self.sub_entry.configure(state="normal")
        self.sub_entry.xview_moveto(1.0)
        self.sub_entry.configure(state="disabled")
        preview = lines[0].text.replace("\n", " ")[:40]
        self.sub_info_label.configure(text=f"{len(lines)} baris  \u00b7  baris pertama: \"{preview}\"")
        self._update_default_output_path()
        self._redraw_preview()

    def _extract_preview_frame(self, video_path, duration_s):
        """Ambil satu frame contoh (sekitar 1/3 durasi) untuk ditampilkan di
        panel preview gaya subtitle - tidak perlu buka video player penuh."""
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return
            target_s = min(max(0.5, duration_s / 3), duration_s if duration_s else 0.5)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_s * fps))
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._preview_frame_pil = Image.fromarray(frame_rgb)
            self._redraw_preview()
        except Exception:
            pass  # preview murni kosmetik, jangan sampai ganggu alur utama

    def _redraw_preview(self):
        if self._preview_frame_pil is None:
            return
        box_w, box_h = 480, 140
        img = self._preview_frame_pil.copy()
        scale = min(box_w / img.width, box_h / img.height)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)

        sample_text = self.subtitle_lines[0].text if self.subtitle_lines else "Contoh Teks Subtitle"
        img = render_subtitle_overlay(img, sample_text, self.subtitle_style,
                                       self.video_dims[0], self.video_dims[1])

        self._preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self._preview_photo, text="")

    def _open_style_dialog(self):
        from .subtitle_style_dialog import SubtitleStyleDialog

        def on_change(style):
            self.subtitle_style = style
            self._redraw_preview()

        SubtitleStyleDialog(self, self.subtitle_style, on_change=on_change)

    def _update_default_output_path(self):
        if not self.video_path:
            return
        base = os.path.splitext(os.path.basename(self.video_path))[0]
        out_dir = os.path.dirname(self.video_path)
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
        path = filedialog.asksaveasfilename(
            defaultextension=ext, filetypes=filetypes, parent=self,
            initialfile=os.path.basename(self.output_path_var.get() or f"output{ext}"))
        if path:
            self.output_path_var.set(path)

    # ----------------------------------------------------------------- run
    def _start_merge(self):
        if self.running:
            return
        if not self.video_path:
            messagebox.showwarning("Belum ada video", "Pilih file video terlebih dahulu.", parent=self)
            return
        if not self.subtitle_lines:
            messagebox.showwarning("Belum ada subtitle", "Pilih file subtitle terlebih dahulu.", parent=self)
            return
        if not video_utils.check_ffmpeg_available():
            messagebox.showerror("ffmpeg tidak ditemukan", "ffmpeg dibutuhkan untuk proses ini.", parent=self)
            return
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showwarning("Lokasi belum dipilih", "Pilih lokasi simpan file terlebih dahulu.",
                                    parent=self)
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="Memulai...")

        lines = list(self.subtitle_lines)
        video_path = self.video_path
        mode = self.mode_var.get()

        if mode == "burnin":
            quality_map = {"Cepat": "cepat", "Sedang": "sedang", "Tinggi": "tinggi"}
            quality = next((v for k, v in quality_map.items()
                             if self.quality_menu.get().startswith(k)), "sedang")

            def task():
                try:
                    self.exporter.export_burned_in(
                        video_path, lines, output_path, quality=quality, style=self.subtitle_style,
                        progress_callback=lambda p, m: self.after(0, self._on_progress, p, m),
                    )
                    self.after(0, self._on_finished, None)
                except VideoExportCancelled:
                    self.after(0, self._on_finished, "Dibatalkan")
                except Exception as exc:
                    self.after(0, self._on_finished, str(exc))
        else:
            rev_lang = {v: k for k, v in LANGUAGES.items()}
            lang_label = self.lang_menu.get()
            lang_code = rev_lang.get(lang_label, "auto")

            def task():
                try:
                    self.exporter.export_embedded(
                        video_path, lines, output_path,
                        include_original=True, include_translated=False,
                        source_lang=lang_code, original_title=lang_label,
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
            messagebox.showerror("Gagal", error, parent=self)

    def _cancel_merge(self):
        self.exporter.cancel()
        self.status_label.configure(text="Membatalkan...")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Proses berjalan", "Proses masih berjalan. Batalkan dan tutup?",
                                        parent=self):
                return
            self.exporter.cancel()
        self.destroy()
