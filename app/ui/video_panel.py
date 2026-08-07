"""Panel preview video: play/pause/seek + overlay subtitle langsung di atas video.

Dekode frame pakai OpenCV, audio diputar terpisah lewat AudioPlayer lalu
disinkronkan dengan estimasi waktu (bukan player broadcast-grade, tapi cukup
akurat untuk keperluan preview & pengecekan sinkronisasi subtitle)."""
import os

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont

from ..core.audio_player import AudioPlayer
from ..utils.constants import resource_path


def _load_overlay_font(size: int):
    candidates = [
        resource_path(os.path.join("assets", "fonts", "NotoSans-Bold.ttf")),
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                try:
                    # NotoSans yang dibundel adalah variable font; pilih instance Bold
                    # supaya overlay subtitle terbaca jelas di atas video apa pun.
                    if "Bold" in font.get_variation_names():
                        font.set_variation_by_name("Bold")
                except Exception:
                    pass
                return font
            except Exception:
                continue
    return ImageFont.load_default()


def _ms_to_hms(ms: int) -> str:
    ms = max(0, int(ms))
    s, _ = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class VideoPanel(ctk.CTkFrame):
    def __init__(self, master, on_time_update=None, get_subtitle_at=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_time_update = on_time_update        # callback(ms) dipanggil berkala saat playback
        self.get_subtitle_at = get_subtitle_at       # callback(ms) -> teks subtitle aktif saat ini

        self.cap = None
        self.fps = 25.0
        self.total_frames = 0
        self.duration_ms = 0
        self.playing = False
        self.burn_in = True
        self.has_video_track = False
        self._font_cache = {}
        self._last_photo = None
        self._slider_dragging = False
        self._media_loaded = False

        self.audio_player = AudioPlayer()
        self._tracked_ms = 0
        self._build()

    # -------------------------------------------------------------- layout
    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        canvas_frame = ctk.CTkFrame(self, fg_color="#101010")
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # tk.Label biasa (bukan CTkLabel) supaya update PhotoImage per-frame stabil & cepat.
        self.video_label = tk.Label(
            canvas_frame, bg="#101010", fg="#666666",
            text="Belum ada media dimuat.\n\nKlik 'Buka Video/Audio' untuk mulai.",
            font=("Segoe UI", 13), justify="center",
        )
        self.video_label.grid(row=0, column=0, sticky="nsew")
        self.video_label.bind("<Configure>", self._on_resize)

        controls = ctk.CTkFrame(self, fg_color="transparent", height=40)
        controls.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        controls.grid_columnconfigure(2, weight=1)

        self.play_btn = ctk.CTkButton(controls, text="\u25B6", width=40, command=self.toggle_play)
        self.play_btn.grid(row=0, column=0, padx=(4, 4))
        self.play_btn.configure(state="disabled")

        self.time_label = ctk.CTkLabel(controls, text="00:00:00 / 00:00:00",
                                        font=ctk.CTkFont(size=11), width=150)
        self.time_label.grid(row=0, column=1, padx=4)

        self.seek_slider = ctk.CTkSlider(controls, from_=0, to=1000, number_of_steps=1000,
                                          command=self._on_slider_drag)
        self.seek_slider.set(0)
        self.seek_slider.grid(row=0, column=2, sticky="ew", padx=8)
        self.seek_slider.configure(state="disabled")
        self.seek_slider.bind("<ButtonPress-1>", self._on_slider_press)
        self.seek_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        self.burn_in_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(controls, text="Overlay subtitle", variable=self.burn_in_var,
                         command=self._on_burn_in_toggle, font=ctk.CTkFont(size=11)
                         ).grid(row=0, column=3, padx=8)

    # --------------------------------------------------------------- media
    def load_media(self, video_path, audio_path: str, has_video: bool):
        import cv2
        self.stop()
        self.release()

        self.has_video_track = has_video
        if has_video:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                self.cap = None
                self.has_video_track = False
            else:
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
                if self.fps <= 0 or self.fps > 240:
                    self.fps = 25.0
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        self.audio_player.load(audio_path)
        if self.cap is not None and self.total_frames > 0:
            self.duration_ms = int((self.total_frames / self.fps) * 1000)
        else:
            self.duration_ms = self.audio_player.duration_ms()

        self._media_loaded = True
        self.play_btn.configure(state="normal")
        self.seek_slider.configure(state="normal")
        if self.cap is None:
            filename = os.path.basename(video_path or audio_path or "")
            self.video_label.configure(text=f"[Mode Audio]\n{filename}", image="")
        self.seek(0)

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def get_duration_ms(self) -> int:
        return self.duration_ms

    def get_current_ms(self) -> int:
        return self._current_ms()

    # ------------------------------------------------------------ playback
    def toggle_play(self):
        self.pause() if self.playing else self.play()

    def play(self):
        if not self._media_loaded:
            return
        if self._current_ms() >= self.duration_ms - 20:
            self.seek(0)
        self.playing = True
        self.play_btn.configure(text="\u23F8")
        self.audio_player.play_from(self._current_ms())
        self._playback_loop()

    def pause(self):
        self.playing = False
        self.play_btn.configure(text="\u25B6")
        self.audio_player.pause()

    def stop(self):
        self.playing = False
        self.play_btn.configure(text="\u25B6")
        self.audio_player.stop()

    def _current_ms(self) -> int:
        if self.cap is not None:
            return self._tracked_ms
        return self.audio_player.current_position_ms()

    def seek(self, ms: int):
        import cv2
        if not self._media_loaded:
            return
        ms = max(0, min(int(ms), max(0, self.duration_ms)))
        was_playing = self.playing
        if was_playing:
            self.audio_player.pause()

        if self.cap is not None:
            frame_idx = int((ms / 1000.0) * self.fps)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if ret:
                self._display_frame(frame, ms)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        self._tracked_ms = ms
        self._update_time_label(ms)
        self._update_slider(ms)
        if was_playing:
            self.audio_player.play_from(ms)

    def _playback_loop(self):
        if not self.playing:
            return
        current_ms = self._current_ms()
        if current_ms >= self.duration_ms:
            self.pause()
            self._update_time_label(self.duration_ms)
            self._update_slider(self.duration_ms)
            return

        if self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                self.pause()
                return
            import cv2
            display_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
            if display_ms <= 0:
                # sebagian backend/codec kadang tidak melaporkan POS_MSEC valid;
                # fallback ke estimasi manual berbasis fps supaya tetap maju.
                display_ms = self._tracked_ms + int(1000 / self.fps)
            self._tracked_ms = display_ms
            self._display_frame(frame, display_ms)
        else:
            display_ms = current_ms
            self._tracked_ms = display_ms

        self._update_time_label(display_ms)
        self._update_slider(display_ms)
        if self.on_time_update:
            self.on_time_update(display_ms)

        delay = max(10, int(1000 / self.fps)) if self.cap is not None else 80
        self.after(delay, self._playback_loop)

    # ------------------------------------------------------------- render
    def _display_frame(self, frame_bgr, current_ms):
        import cv2
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        panel_w = max(self.video_label.winfo_width(), 160)
        panel_h = max(self.video_label.winfo_height(), 90)
        img = self._fit_image(img, panel_w, panel_h)

        if self.burn_in and self.get_subtitle_at:
            text = self.get_subtitle_at(current_ms)
            if text:
                img = self._draw_subtitle_overlay(img, text)

        photo = ImageTk.PhotoImage(img)
        self.video_label.configure(image=photo, text="")
        self._last_photo = photo

    def _fit_image(self, img, box_w, box_h):
        img_w, img_h = img.size
        if img_w == 0 or img_h == 0:
            return img
        scale = max(0.05, min(box_w / img_w, box_h / img_h))
        new_w, new_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))
        return img.resize((new_w, new_h), Image.LANCZOS)

    def _draw_subtitle_overlay(self, img, text):
        img = img.copy()
        draw = ImageDraw.Draw(img)
        font_size = max(13, img.height // 15)
        font = self._get_font(font_size)
        lines = text.split("\n")[:2]  # maksimal 2 baris supaya tidak menutupi video

        heights, widths = [], []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=2)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        total_h = sum(heights) + max(0, len(lines) - 1) * 4
        y = img.height - total_h - int(img.height * 0.06)

        for i, line in enumerate(lines):
            w = widths[i]
            x = (img.width - w) // 2
            draw.text((x, y), line, font=font, fill="white", stroke_width=2, stroke_fill="black")
            y += heights[i] + 4
        return img

    def _get_font(self, size):
        if size not in self._font_cache:
            self._font_cache[size] = _load_overlay_font(size)
        return self._font_cache[size]

    # -------------------------------------------------------------- events
    def _update_time_label(self, ms):
        self.time_label.configure(text=f"{_ms_to_hms(ms)} / {_ms_to_hms(self.duration_ms)}")

    def _update_slider(self, ms):
        if self._slider_dragging or self.duration_ms <= 0:
            return
        frac = max(0.0, min(1.0, ms / self.duration_ms))
        self.seek_slider.set(frac * 1000)

    def _on_slider_press(self, _event=None):
        self._slider_dragging = True

    def _on_slider_drag(self, value):
        if self._slider_dragging and self.duration_ms > 0:
            ms = int(value / 1000 * self.duration_ms)
            self._update_time_label(ms)

    def _on_slider_release(self, _event=None):
        self._slider_dragging = False
        if self.duration_ms > 0:
            ms = int(self.seek_slider.get() / 1000 * self.duration_ms)
            self.seek(ms)
            if self.on_time_update:
                self.on_time_update(ms)

    def _on_burn_in_toggle(self):
        self.burn_in = self.burn_in_var.get()
        if self._media_loaded and not self.playing:
            self.seek(self._current_ms())

    def _on_resize(self, _event=None):
        if self._media_loaded and self.cap is not None and not self.playing:
            self.seek(self._current_ms())

    def destroy(self):
        self.release()
        try:
            self.audio_player.stop()
        except Exception:
            pass
        super().destroy()
