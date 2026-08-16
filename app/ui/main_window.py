"""Jendela utama MaxSubtitle: menyatukan toolbar, preview video, waveform,
editor grid, dan seluruh alur kerja transkripsi -> terjemahan -> export."""
import os
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..core import formats, video_utils, waveform
from ..core.subtitle import SubtitleDocument
from ..core.subtitle_style import SubtitleStyle
from ..core.transcriber import Transcriber, TranscribeCancelled
from ..core.translator import Translator, TranslateCancelled
from ..utils.config import ConfigManager
from ..utils.constants import (
    APP_NAME, APP_VERSION, COPYRIGHT_FULL, SUPPORTED_VIDEO_EXT, SUPPORTED_AUDIO_EXT,
    get_color_theme_path,
)

from .toolbar import Toolbar
from .editor_panel import EditorPanel, style_treeview
from .video_panel import VideoPanel
from .waveform_panel import WaveformPanel
from .settings_dialog import SettingsDialog
from .batch_dialog import BatchDialog
from .video_export_dialog import VideoExportDialog
from .quick_merge_dialog import QuickMergeDialog
from .footer import Footer


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()

        self.doc = SubtitleDocument()
        self._temp_audio_path = None
        self._current_transcriber = None
        self._current_translator = None
        self._busy = False

        self.title(APP_NAME)
        geometry = self.config_manager.get("window_geometry") or "1280x800"
        self.geometry(geometry)
        self.minsize(1000, 650)

        theme = self.config_manager.get("theme")
        ctk.set_appearance_mode(theme if theme in ("dark", "light", "system") else "dark")
        ctk.set_default_color_theme(get_color_theme_path())

        self._build_layout()
        style_treeview(self, dark=(theme != "light"))
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- layout
    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.toolbar = Toolbar(self, callbacks=self._toolbar_callbacks())
        self.toolbar.grid(row=0, column=0, sticky="ew")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=3)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=2)

        self.video_panel = VideoPanel(body, on_time_update=self._on_playback_time,
                                       get_subtitle_at=self._get_subtitle_at)
        self.video_panel.grid(row=0, column=0, sticky="nsew", pady=(6, 4))
        self.video_panel.subtitle_style = SubtitleStyle.from_dict(
            self.config_manager.get("subtitle_style", {}))
        self.video_panel._open_style_dialog = self._open_style_dialog

        self.waveform_panel = WaveformPanel(body, on_seek=self._on_waveform_seek,
                                             on_region_change=self._on_region_change, height=120)
        self.waveform_panel.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.waveform_panel.pack_propagate(False)

        self.editor_panel = EditorPanel(body, on_select=self._on_editor_select,
                                         on_change=self._on_editor_change,
                                         on_request_seek=self._on_request_seek)
        self.editor_panel.grid(row=2, column=0, sticky="nsew", pady=(0, 6))

        self.footer = Footer(self)
        self.footer.grid(row=2, column=0, sticky="ew")

    def _toolbar_callbacks(self):
        return {
            "open_media": self._open_media,
            "open_subtitle": self._open_subtitle,
            "save": self._save,
            "export_srt": lambda: self._export_format("srt", use_translated=self._any_translated()),
            "export_vtt": lambda: self._export_format("vtt", use_translated=self._any_translated()),
            "export_ass": lambda: self._export_format("ass", use_translated=self._any_translated()),
            "export_txt": lambda: self._export_format("txt", use_translated=self._any_translated()),
            "export_srt_bilingual": lambda: self._export_format("srt", bilingual=True),
            "auto_process": self._auto_process,
            "transcribe": self._transcribe,
            "translate": self._translate,
            "cancel": self._cancel_processing,
            "batch": self._open_batch,
            "settings": self._open_settings,
            "export_video": self._open_video_export,
            "quick_merge": self._open_quick_merge,
            "about": self._show_about,
        }

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self._open_media())
        self.bind("<Control-s>", lambda e: self._save())
        self.bind("<space>", self._on_space_key)

    def _on_space_key(self, event):
        widget = self.focus_get()
        if isinstance(widget, (tk.Entry, tk.Text)):
            return None
        if widget is not None and widget.winfo_class() in ("Entry", "Text", "TEntry"):
            return None
        if self.video_panel._media_loaded:
            self.video_panel.toggle_play()
        return "break"

    # --------------------------------------------------------- media I/O
    def _open_media(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED_VIDEO_EXT + SUPPORTED_AUDIO_EXT)
        path = filedialog.askopenfilename(
            title="Buka video atau audio",
            filetypes=[("Video & Audio", exts), ("Semua file", "*.*")],
            initialdir=self.config_manager.get("last_open_dir") or None,
        )
        if not path:
            return
        self.config_manager.set("last_open_dir", os.path.dirname(path))
        self.config_manager.save()
        self._load_media_file(path)

    def _load_media_file(self, path):
        if not video_utils.check_ffmpeg_available():
            messagebox.showerror(
                "ffmpeg tidak ditemukan",
                "MaxSubtitle butuh ffmpeg untuk membaca audio/video.\n\n"
                "Unduh dari ffmpeg.org lalu tambahkan ke PATH Windows,\n"
                "atau taruh ffmpeg.exe & ffprobe.exe di folder 'ffmpeg' "
                "di sebelah MaxSubtitle.exe.",
            )
            return

        def task():
            try:
                self.after(0, self._set_busy, True, "Membaca info media...")
                info = video_utils.get_media_info(path)
                is_video = video_utils.is_video_file(path) and info.get("has_video", False)
                if not is_video and not info.get("has_audio", False) and not video_utils.is_audio_file(path):
                    raise RuntimeError("File tidak memiliki track audio yang bisa dibaca.")

                self._cleanup_temp_audio()
                fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="maxsub_")
                os.close(fd)
                self._temp_audio_path = tmp_path

                self.after(0, self._set_busy, True, "Mengekstrak audio...")
                video_utils.extract_audio(path, self._temp_audio_path)

                self.after(0, self._on_media_loaded, path, is_video)
            except Exception as exc:
                self.after(0, messagebox.showerror, "Gagal membuka media", str(exc))
                self.after(0, self._set_busy, False, "Gagal memuat media")

        threading.Thread(target=task, daemon=True).start()

    def _on_media_loaded(self, path, is_video):
        self.doc = SubtitleDocument()
        self.doc.video_path = path if is_video else None
        self.doc.audio_path = self._temp_audio_path
        self.doc.target_language = self.config_manager.get("target_language")

        self.video_panel.load_media(path if is_video else None, self._temp_audio_path, is_video)
        self.editor_panel.refresh([])
        self.waveform_panel.clear()
        self.title(f"{APP_NAME} - {os.path.basename(path)}")
        self._set_busy(False, f"Media dimuat: {os.path.basename(path)}. Siap diproses.")
        self._load_waveform_async()

    def _load_waveform_async(self):
        audio_path = self._temp_audio_path

        def task():
            try:
                peaks, _sr, _total = waveform.generate_peaks(audio_path, num_points=2400)
                duration_ms = self.video_panel.get_duration_ms()
                self.after(0, self._apply_waveform, peaks, duration_ms)
            except Exception:
                pass  # waveform murni kosmetik, jangan ganggu alur utama kalau gagal

        threading.Thread(target=task, daemon=True).start()

    def _apply_waveform(self, peaks, duration_ms):
        self.waveform_panel.set_waveform(peaks, duration_ms)
        self.waveform_panel.set_lines(self.doc.lines)

    def _open_subtitle(self):
        path = filedialog.askopenfilename(
            title="Buka file subtitle",
            filetypes=[("Subtitle", "*.srt *.vtt"), ("Semua file", "*.*")],
        )
        if not path:
            return
        try:
            lines = formats.load_subtitle_file(path)
        except Exception as exc:
            messagebox.showerror("Gagal membuka subtitle", str(exc))
            return
        self.doc.set_lines(lines)
        self._on_lines_updated()
        self.footer.set_status(f"Subtitle dimuat: {os.path.basename(path)} ({len(lines)} baris)")

    def _any_translated(self):
        return any(l.translated_text for l in self.doc.lines)

    def _save(self):
        self._export_format("srt", use_translated=self._any_translated())

    def _export_format(self, fmt, use_translated=False, bilingual=False):
        if not self.doc.lines:
            messagebox.showwarning("Belum ada data", "Belum ada subtitle untuk diexport.")
            return
        default_name = "subtitle"
        if self.doc.video_path:
            default_name = os.path.splitext(os.path.basename(self.doc.video_path))[0]
        ext_map = {"srt": ".srt", "vtt": ".vtt", "ass": ".ass", "txt": ".txt"}
        suffix = "_dwibahasa" if bilingual else ""
        path = filedialog.asksaveasfilename(
            defaultextension=ext_map[fmt],
            initialfile=default_name + suffix + ext_map[fmt],
            filetypes=[(fmt.upper(), f"*{ext_map[fmt]}")],
            initialdir=self.config_manager.get("last_export_dir") or None,
        )
        if not path:
            return
        self.config_manager.set("last_export_dir", os.path.dirname(path))
        self.config_manager.save()
        try:
            if fmt == "srt":
                formats.write_srt(self.doc.lines, path, use_translated=use_translated, bilingual=bilingual)
            elif fmt == "vtt":
                formats.write_vtt(self.doc.lines, path, use_translated=use_translated, bilingual=bilingual)
            elif fmt == "ass":
                formats.write_ass(self.doc.lines, path, use_translated=use_translated, bilingual=bilingual)
            elif fmt == "txt":
                formats.write_txt(self.doc.lines, path, use_translated=use_translated)
            self.doc.dirty = False
            self.footer.set_status(f"Tersimpan: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Gagal menyimpan", str(exc))

    # ------------------------------------------------------------- AI ops
    def _transcribe(self):
        if self._busy:
            return
        if not self.doc.audio_path:
            messagebox.showwarning("Belum ada media", "Buka file video/audio terlebih dahulu.")
            return
        self._current_transcriber = Transcriber(
            model_size=self.config_manager.get("model_size"), device=self.config_manager.get("device"))

        def task():
            try:
                self.after(0, self._set_busy, True, "Memulai transkripsi...")
                lines, detected = self._current_transcriber.transcribe(
                    self.doc.audio_path,
                    language=self.config_manager.get("source_language"),
                    progress_callback=lambda pct, msg: self.after(0, self._update_progress, pct, msg),
                )
                self.doc.set_lines(lines)
                self.doc.source_language = detected
                self.after(0, self._on_lines_updated)
                self.after(0, self._set_busy, False, f"Transkripsi selesai: {len(lines)} baris (bahasa: {detected})")
            except TranscribeCancelled:
                self.after(0, self._set_busy, False, "Transkripsi dibatalkan")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Error Transkripsi", str(exc))
                self.after(0, self._set_busy, False, "Gagal melakukan transkripsi")
            finally:
                self._current_transcriber = None

        threading.Thread(target=task, daemon=True).start()

    def _translate(self):
        if self._busy:
            return
        if not self.doc.lines:
            messagebox.showwarning(
                "Belum ada teks",
                "Belum ada teks subtitle untuk diterjemahkan.\nLakukan transkripsi dulu, atau buka file subtitle.",
            )
            return
        self._current_translator = Translator(source="auto", target=self.config_manager.get("target_language"))

        def task():
            try:
                self.after(0, self._set_busy, True, "Memulai terjemahan...")
                texts = [l.text for l in self.doc.lines]
                translated = self._current_translator.translate_batch(
                    texts, progress_callback=lambda pct, msg: self.after(0, self._update_progress, pct, msg))
                for line, t in zip(self.doc.lines, translated):
                    line.translated_text = t
                self.after(0, self._on_lines_updated)
                self.after(0, self._set_busy, False, "Terjemahan selesai")
            except TranslateCancelled:
                self.after(0, self._set_busy, False, "Terjemahan dibatalkan")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Error Terjemahan", str(exc))
                self.after(0, self._set_busy, False, "Gagal menerjemahkan")
            finally:
                self._current_translator = None

        threading.Thread(target=task, daemon=True).start()

    def _auto_process(self):
        if self._busy:
            return
        if not self.doc.audio_path:
            messagebox.showwarning("Belum ada media", "Buka file video/audio terlebih dahulu.")
            return
        self._current_transcriber = Transcriber(
            model_size=self.config_manager.get("model_size"), device=self.config_manager.get("device"))
        self._current_translator = Translator(source="auto", target=self.config_manager.get("target_language"))

        def task():
            try:
                self.after(0, self._set_busy, True, "Memulai proses otomatis (transkripsi + terjemahan)...")
                lines, detected = self._current_transcriber.transcribe(
                    self.doc.audio_path,
                    language=self.config_manager.get("source_language"),
                    progress_callback=lambda pct, msg: self.after(0, self._update_progress, pct * 0.5, msg),
                )
                self.doc.set_lines(lines)
                self.doc.source_language = detected
                self.after(0, self._on_lines_updated)

                texts = [l.text for l in self.doc.lines]
                translated = self._current_translator.translate_batch(
                    texts,
                    progress_callback=lambda pct, msg: self.after(0, self._update_progress, 50 + pct * 0.5, msg),
                )
                for line, t in zip(self.doc.lines, translated):
                    line.translated_text = t
                self.after(0, self._on_lines_updated)
                target = self.config_manager.get("target_language")
                self.after(0, self._set_busy, False,
                           f"Selesai! {len(lines)} baris diterjemahkan ({detected} -> {target})")
            except (TranscribeCancelled, TranslateCancelled):
                self.after(0, self._set_busy, False, "Dibatalkan")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Error", str(exc))
                self.after(0, self._set_busy, False, "Gagal")
            finally:
                self._current_transcriber = None
                self._current_translator = None

        threading.Thread(target=task, daemon=True).start()

    def _cancel_processing(self):
        if self._current_transcriber:
            self._current_transcriber.cancel()
        if self._current_translator:
            self._current_translator.cancel()
        self.footer.set_status("Membatalkan...")

    def _on_lines_updated(self):
        self.editor_panel.refresh(self.doc.lines)
        self.waveform_panel.set_lines(self.doc.lines)

    # -------------------------------------------------------- panel sync
    def _on_editor_select(self, line):
        self.waveform_panel.set_selected(line)
        if self.video_panel._media_loaded and not self.video_panel.playing:
            self.video_panel.seek(line.start_ms)
            self.waveform_panel.set_playhead(line.start_ms)

    def _on_editor_change(self, action=None):
        if action == "add_line":
            current_ms = self.video_panel.get_current_ms() if self.video_panel._media_loaded else 0
            new_line = self.doc.add_line(current_ms, current_ms + 2000, "")
            self._on_lines_updated()
            self.editor_panel.select_line(new_line)
        elif action == "duplicate_line" and self.editor_panel.current_line:
            new_line = self.doc.duplicate_line(self.editor_panel.current_line)
            self._on_lines_updated()
            if new_line:
                self.editor_panel.select_line(new_line)
        elif action == "merge_next" and self.editor_panel.current_line:
            merged = self.doc.merge_with_next(self.editor_panel.current_line)
            self._on_lines_updated()
            if merged:
                self.editor_panel.select_line(merged)
        elif action == "split_current" and self.editor_panel.current_line:
            line = self.editor_panel.current_line
            text = line.text
            mid = len(text) // 2
            split_pos = text.rfind(" ", 0, mid) if mid > 0 else -1
            if split_pos <= 0:
                split_pos = mid if mid > 0 else min(1, len(text) - 1) if len(text) > 1 else 0
            if 0 < split_pos < len(text):
                self.doc.split_line(line, split_pos)
                self._on_lines_updated()
                self.editor_panel.select_line(line)
        elif action == "delete_line" and self.editor_panel.current_line:
            self.doc.remove_line(self.editor_panel.current_line)
            self._on_lines_updated()
        else:
            # edit teks/waktu manual dari kotak edit - baris sudah di-refresh sendiri
            # oleh EditorPanel; cukup segarkan wilayah di waveform.
            self.doc.dirty = True
            self.waveform_panel.set_lines(self.doc.lines)

    def _on_request_seek(self, ms):
        if self.video_panel._media_loaded:
            self.video_panel.seek(ms)
        self.waveform_panel.set_playhead(ms)

    def _on_waveform_seek(self, ms):
        if self.video_panel._media_loaded:
            self.video_panel.seek(ms)
        self.waveform_panel.set_playhead(ms)
        line = self.doc.line_at_time(ms)
        if line:
            self.editor_panel.select_line(line, notify=False)
            self.waveform_panel.set_selected(line)

    def _on_region_change(self, line, _new_start, _new_end):
        self.doc.dirty = True
        self.doc.sort_by_time()
        self.editor_panel.refresh(self.doc.lines)
        self.waveform_panel.set_lines(self.doc.lines)
        self.waveform_panel.set_selected(line)

    def _on_playback_time(self, ms):
        self.waveform_panel.set_playhead(ms)
        line = self.doc.line_at_time(ms)
        if line is not None and line is not self.editor_panel.current_line:
            self.editor_panel.select_line(line, notify=False)
            self.waveform_panel.set_selected(line)

    def _get_subtitle_at(self, ms):
        line = self.doc.line_at_time(ms)
        if not line:
            return ""
        return line.translated_text or line.text

    # ------------------------------------------------------------- status
    def _set_busy(self, busy, status_text=None):
        self._busy = busy
        self.toolbar.set_busy(busy)
        if status_text:
            self.footer.set_status(status_text)
        self.footer.set_progress(0 if busy else None)

    def _update_progress(self, pct, msg):
        self.footer.set_progress(pct / 100.0)
        self.footer.set_status(msg)

    # ------------------------------------------------------------ dialogs
    def _open_settings(self):
        SettingsDialog(self, self.config_manager, on_save=self._apply_saved_settings)

    def _apply_saved_settings(self):
        theme = self.config_manager.get("theme")
        ctk.set_appearance_mode(theme if theme in ("dark", "light", "system") else "dark")
        style_treeview(self, dark=(theme != "light"))
        self.editor_panel.refresh(self.doc.lines)

    def _open_batch(self):
        BatchDialog(self, self.config_manager)

    def _open_style_dialog(self):
        from .subtitle_style_dialog import SubtitleStyleDialog
        SubtitleStyleDialog(
            self, self.video_panel.subtitle_style,
            on_change=self.video_panel.set_subtitle_style,
            on_close=self._on_style_dialog_closed,
        )

    def _on_style_dialog_closed(self, style):
        self.video_panel.set_subtitle_style(style)
        self.config_manager.set("subtitle_style", style.to_dict())
        self.config_manager.save()

    def _open_video_export(self):
        if not self.doc.video_path:
            messagebox.showwarning(
                "Tidak ada video",
                "Export video butuh file video asli yang sedang dibuka (bukan mode audio-saja).\n\n"
                "Buka file video dulu lewat 'Buka Video/Audio'.",
            )
            return
        if not self.doc.lines:
            messagebox.showwarning("Belum ada subtitle", "Belum ada baris subtitle untuk diexport.")
            return
        VideoExportDialog(self, self.doc, self.config_manager, self.video_panel.subtitle_style)

    def _open_quick_merge(self):
        QuickMergeDialog(self)

    def _show_about(self):
        messagebox.showinfo(
            "Tentang MaxSubtitle",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "Transkripsi & terjemahan subtitle video otomatis berbasis AI\n"
            "(faster-whisper + Google Translate).\n\n"
            f"{COPYRIGHT_FULL}",
        )

    # -------------------------------------------------------------- close
    def _on_close(self):
        if self._busy:
            if not messagebox.askyesno("Proses berjalan", "Proses AI masih berjalan. Tutup paksa aplikasi?"):
                return
            self._cancel_processing()
        try:
            self.config_manager.set("window_geometry", self.geometry())
            self.config_manager.save()
        except Exception:
            pass
        self._cleanup_temp_audio()
        try:
            self.video_panel.release()
        except Exception:
            pass
        self.destroy()

    def _cleanup_temp_audio(self):
        if self._temp_audio_path and os.path.exists(self._temp_audio_path):
            try:
                os.remove(self._temp_audio_path)
            except OSError:
                pass
        self._temp_audio_path = None
