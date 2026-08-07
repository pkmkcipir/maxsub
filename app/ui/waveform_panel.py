"""Panel waveform: gambar amplitudo audio + kotak wilayah tiap baris subtitle.
Klik = pindah posisi putar. Drag tepi kiri/kanan wilayah baris terpilih = ubah
waktu mulai/selesai baris itu langsung secara visual."""
import tkinter as tk

import customtkinter as ctk

HANDLE_PX = 6


class WaveformPanel(ctk.CTkFrame):
    def __init__(self, master, on_seek=None, on_region_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_seek = on_seek                    # callback(ms)
        self.on_region_change = on_region_change   # callback(line, new_start_ms, new_end_ms)

        self.peaks = []
        self.duration_ms = 0
        self.lines = []
        self.selected_line = None
        self.playhead_ms = 0

        self._drag_mode = None   # None | "start" | "end" | "seek"
        self._drag_line = None

        self.canvas = tk.Canvas(self, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self._empty_state()

    # ------------------------------------------------------------- data in
    def set_waveform(self, peaks, duration_ms: int):
        self.peaks = peaks or []
        self.duration_ms = max(1, duration_ms)
        self._redraw()

    def set_lines(self, lines):
        self.lines = lines
        self._redraw()

    def set_selected(self, line):
        self.selected_line = line
        self._redraw()

    def set_playhead(self, ms: int):
        self.playhead_ms = ms
        self._redraw_playhead_only()

    def clear(self):
        self.peaks = []
        self.duration_ms = 0
        self.lines = []
        self.selected_line = None
        self.playhead_ms = 0
        self._empty_state()

    # -------------------------------------------------------------- helpers
    def _empty_state(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 200)
        h = max(self.canvas.winfo_height(), 100)
        self.canvas.create_text(w // 2, h // 2, text="Waveform akan tampil di sini setelah media dimuat",
                                 fill="#555555", font=("Segoe UI", 10))

    def _ms_to_x(self, ms: int, width: int) -> float:
        if self.duration_ms <= 0:
            return 0
        return (ms / self.duration_ms) * width

    def _x_to_ms(self, x: float, width: int) -> int:
        if width <= 0:
            return 0
        frac = max(0.0, min(1.0, x / width))
        return int(frac * self.duration_ms)

    # ---------------------------------------------------------------- draw
    def _redraw(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 10 or height < 10:
            return
        if not self.peaks or self.duration_ms <= 0:
            self._empty_state()
            return

        self._draw_waveform(width, height)
        self._draw_regions(width, height)
        self._draw_playhead(width, height)

    def _draw_waveform(self, width, height):
        mid = height / 2
        n = len(self.peaks)
        if n == 0:
            return
        step = width / n
        bar_w = max(1.0, step * 0.8)
        for i, p in enumerate(self.peaks):
            x = i * step
            bar_h = max(1.0, p * (height * 0.42))
            self.canvas.create_rectangle(x, mid - bar_h, x + bar_w, mid + bar_h,
                                          fill="#3d8bd4", outline="", tags="wave")

    def _draw_regions(self, width, height):
        for line in self.lines:
            x1 = self._ms_to_x(line.start_ms, width)
            x2 = self._ms_to_x(line.end_ms, width)
            is_selected = line is self.selected_line
            fill = "#2fa572" if is_selected else "#666666"
            self.canvas.create_rectangle(x1, 2, x2, 14, fill=fill, outline="",
                                          tags=("region", f"region-{id(line)}"))
            label = line.text[:40] if line.text else "(kosong)"
            if x2 - x1 > 20:
                self.canvas.create_text(x1 + 3, 8, text=label, fill="white", anchor="w",
                                         font=("Segoe UI", 7), tags="region")
            if is_selected:
                self.canvas.create_line(x1, 0, x1, height, fill="#2fa572", width=2, tags="handle-start")
                self.canvas.create_line(x2, 0, x2, height, fill="#e05252", width=2, tags="handle-end")

    def _draw_playhead(self, width, height):
        x = self._ms_to_x(self.playhead_ms, width)
        self.canvas.create_line(x, 0, x, height, fill="#ffffff", width=1, tags="playhead")

    def _redraw_playhead_only(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 10 or height < 10:
            return
        self.canvas.delete("playhead")
        self._draw_playhead(width, height)

    # -------------------------------------------------------------- events
    def _on_press(self, event):
        width = self.canvas.winfo_width()
        if width <= 0 or self.duration_ms <= 0:
            return
        if self.selected_line is not None:
            x1 = self._ms_to_x(self.selected_line.start_ms, width)
            x2 = self._ms_to_x(self.selected_line.end_ms, width)
            if abs(event.x - x1) <= HANDLE_PX:
                self._drag_mode = "start"
                self._drag_line = self.selected_line
                return
            if abs(event.x - x2) <= HANDLE_PX:
                self._drag_mode = "end"
                self._drag_line = self.selected_line
                return
        self._drag_mode = "seek"
        ms = self._x_to_ms(event.x, width)
        if self.on_seek:
            self.on_seek(ms)

    def _on_drag(self, event):
        width = self.canvas.winfo_width()
        if width <= 0 or self._drag_mode is None:
            return
        ms = self._x_to_ms(event.x, width)
        if self._drag_mode == "seek":
            if self.on_seek:
                self.on_seek(ms)
        elif self._drag_mode == "start" and self._drag_line is not None:
            new_start = min(ms, self._drag_line.end_ms - 100)
            new_start = max(0, new_start)
            self._drag_line.start_ms = new_start
            self._redraw()
        elif self._drag_mode == "end" and self._drag_line is not None:
            new_end = max(ms, self._drag_line.start_ms + 100)
            self._drag_line.end_ms = new_end
            self._redraw()

    def _on_release(self, _event):
        if self._drag_mode in ("start", "end") and self._drag_line is not None:
            if self.on_region_change:
                self.on_region_change(self._drag_line, self._drag_line.start_ms, self._drag_line.end_ms)
        self._drag_mode = None
        self._drag_line = None
