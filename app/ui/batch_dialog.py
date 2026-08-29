"""Dialog proses batch: transkripsi + terjemahan + export banyak file sekaligus, tanpa dijaga."""
import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core import formats, video_utils
from ..core.transcriber import Transcriber, TranscribeCancelled
from ..core.translator import Translator, TranslateCancelled
from ..utils.constants import (
    SUPPORTED_VIDEO_EXT, SUPPORTED_AUDIO_EXT, TARGET_LANGUAGES,
    COLOR_SECONDARY, COLOR_SECONDARY_HOVER, COLOR_DANGER, COLOR_DANGER_HOVER,
)


class BatchDialog(ctk.CTkToplevel):
    def __init__(self, master, config_manager):
        super().__init__(master)
        self.config_manager = config_manager
        self.files = []
        self.running = False
        self.cancel_requested = False

        self.title("Proses Batch - MaxSubtitle")
        self.geometry("620x520")
        self.transient(master)
        self.grab_set()

        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkButton(top, text="+ Tambah File", width=120, command=self._add_files).pack(side="left")
        ctk.CTkButton(top, text="Kosongkan", width=100, command=self._clear_files).pack(side="left", padx=6)
        ctk.CTkLabel(top, text="(hapus file satuan lewat tombol X di tiap baris)",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60")).pack(side="left", padx=8)

        self.listbox_frame = ctk.CTkScrollableFrame(self, height=200)
        self.listbox_frame.pack(fill="both", expand=True, padx=16, pady=4)
        self._row_widgets = []

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(opts, text="Bahasa target:").pack(side="left")
        self.target_menu = ctk.CTkOptionMenu(opts, values=list(TARGET_LANGUAGES.values()), width=160)
        current_target = self.config_manager.get("target_language")
        self.target_menu.set(TARGET_LANGUAGES.get(current_target, TARGET_LANGUAGES["id"]))
        self.target_menu.pack(side="left", padx=8)

        self.output_dir_var = ctk.StringVar(value="")
        ctk.CTkButton(opts, text="Pilih Folder Output", width=150,
                      command=self._pick_output_dir).pack(side="left", padx=8)
        self.output_dir_label = ctk.CTkLabel(opts, text="(sama dengan folder file asal)",
                                              font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"))
        self.output_dir_label.pack(side="left")

        self.log_box = ctk.CTkTextbox(self, height=120)
        self.log_box.pack(fill="x", padx=16, pady=8)
        self.log_box.configure(state="disabled")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 16))
        self.start_btn = ctk.CTkButton(bottom, text="Mulai Proses", fg_color=COLOR_SECONDARY,
                                        hover_color=COLOR_SECONDARY_HOVER, command=self._start)
        self.start_btn.pack(side="left")
        self.cancel_btn = ctk.CTkButton(bottom, text="Batal", fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
                                         command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ctk.CTkButton(bottom, text="Tutup", width=90, command=self._on_close).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- file list
    def _add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_VIDEO_EXT + SUPPORTED_AUDIO_EXT)
        paths = filedialog.askopenfilenames(
            title="Pilih video/audio untuk diproses",
            filetypes=[("Video & Audio", exts), ("Semua file", "*.*")],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh_list()

    def _clear_files(self):
        if self.running:
            return
        self.files = []
        self._refresh_list()

    def _refresh_list(self):
        for w in self.listbox_frame.winfo_children():
            w.destroy()
        for i, path in enumerate(self.files):
            row = ctk.CTkFrame(self.listbox_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=os.path.basename(path), anchor="w").pack(side="left", fill="x", expand=True)
            status = ctk.CTkLabel(row, text="menunggu", width=90, text_color=("gray40", "gray60"))
            status.pack(side="left", padx=4)
            remove_btn = ctk.CTkButton(row, text="X", width=28,
                                        command=lambda p=path: self._remove_file(p))
            remove_btn.pack(side="left")
            row._status_label = status  # simpan referensi untuk update status nanti

    def _remove_file(self, path):
        if self.running:
            return
        if path in self.files:
            self.files.remove(path)
        self._refresh_list()

    def _pick_output_dir(self):
        d = filedialog.askdirectory(title="Pilih folder output")
        if d:
            self.output_dir_var.set(d)
            self.output_dir_label.configure(text=d)

    # ------------------------------------------------------------------ log
    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # -------------------------------------------------------------- process
    def _start(self):
        if not self.files:
            messagebox.showwarning("Peringatan", "Tambahkan minimal satu file terlebih dahulu.", parent=self)
            return
        if not video_utils.check_ffmpeg_available():
            messagebox.showerror("Error", "ffmpeg tidak ditemukan. Tidak bisa memproses.", parent=self)
            return

        rev_target = {v: k for k, v in TARGET_LANGUAGES.items()}
        target_lang = rev_target.get(self.target_menu.get(), "id")
        model_size = self.config_manager.get("model_size")
        device = self.config_manager.get("device")
        source_lang = self.config_manager.get("source_language")
        output_dir = self.output_dir_var.get() or None

        self.running = True
        self.cancel_requested = False
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")

        thread = threading.Thread(
            target=self._run_batch,
            args=(list(self.files), model_size, device, source_lang, target_lang, output_dir),
            daemon=True,
        )
        thread.start()

    def _cancel(self):
        self.cancel_requested = True
        self._log("Membatalkan setelah file saat ini selesai...")

    def _run_batch(self, files, model_size, device, source_lang, target_lang, output_dir):
        transcriber = Transcriber(model_size=model_size, device=device)
        total = len(files)
        for i, path in enumerate(files):
            if self.cancel_requested:
                self.after(0, self._log, "Dibatalkan oleh pengguna.")
                break
            self.after(0, self._log, f"[{i+1}/{total}] Memproses: {os.path.basename(path)}")
            try:
                base_progress = i / total
                audio_path = path
                if video_utils.is_video_file(path):
                    tmp_wav = os.path.splitext(path)[0] + "_maxsub_tmp.wav"
                    video_utils.extract_audio(path, tmp_wav)
                    audio_path = tmp_wav

                def progress_cb(pct, msg, base=base_progress):
                    frac = base + (pct / 100.0) * (0.5 / total)
                    self.after(0, self.progress_bar.set, frac)

                lines, detected = transcriber.transcribe(audio_path, language=source_lang,
                                                           progress_callback=progress_cb)
                self.after(0, self._log, f"  -> Transkripsi: {len(lines)} baris (bahasa: {detected})")

                translator = Translator(
                    source="auto", target=target_lang,
                    use_libretranslate=self.config_manager.get("use_libretranslate", False),
                    libretranslate_url=self.config_manager.get("libretranslate_url", "http://localhost:5000/"),
                    libretranslate_api_key=self.config_manager.get("libretranslate_api_key", ""),
                )

                def trans_cb(pct, msg, base=base_progress):
                    frac = base + 0.5 / total + (pct / 100.0) * (0.5 / total)
                    self.after(0, self.progress_bar.set, frac)

                texts = [l.text for l in lines]
                translated = translator.translate_batch(texts, progress_callback=trans_cb)
                for line, t in zip(lines, translated):
                    line.translated_text = t
                if translator.failed_count:
                    self.after(0, self._log,
                               f"  -> Peringatan: {translator.failed_count} baris gagal "
                               f"diterjemahkan, teks asli dipertahankan pada baris itu.")

                out_dir = output_dir or os.path.dirname(path)
                out_name = os.path.splitext(os.path.basename(path))[0] + ".srt"
                out_path = os.path.join(out_dir, out_name)
                formats.write_srt(lines, out_path, use_translated=True)
                self.after(0, self._log, f"  -> Disimpan: {out_path}")

                if audio_path != path and os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except OSError:
                        pass
            except (TranscribeCancelled, TranslateCancelled):
                self.after(0, self._log, "Dibatalkan.")
                break
            except Exception as exc:
                self.after(0, self._log, f"  -> GAGAL: {exc}")

        self.after(0, self._finish_batch)

    def _finish_batch(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        self._log("Selesai.")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Proses berjalan",
                                        "Proses batch masih berjalan. Tutup jendela ini?", parent=self):
                return
        self.destroy()
