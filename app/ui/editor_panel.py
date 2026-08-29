"""Panel editor subtitle: daftar (grid) di kiri + kotak edit baris terpilih di kanan."""
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from ..core.subtitle import SubtitleLine, ms_to_short_time, parse_flexible_time
from ..utils.constants import (
    COLOR_PRIMARY, COLOR_BG_DARK, COLOR_BG_DARK_SURFACE, COLOR_DANGER, COLOR_DANGER_HOVER,
)

COLUMNS = ("no", "mulai", "selesai", "durasi", "teks", "terjemahan")
HEADINGS = {"no": "No", "mulai": "Mulai", "selesai": "Selesai", "durasi": "Durasi",
            "teks": "Teks Asli", "terjemahan": "Terjemahan"}
WIDTHS = {"no": 40, "mulai": 85, "selesai": 85, "durasi": 55, "teks": 280, "terjemahan": 280}


def style_treeview(root, dark: bool = True):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    if dark:
        bg, fg, field_bg, head_bg = COLOR_BG_DARK_SURFACE, "#e6e6e6", COLOR_BG_DARK_SURFACE, COLOR_BG_DARK
        sel = COLOR_PRIMARY
    else:
        bg, fg, field_bg, head_bg = "#ffffff", "#1a1a1a", "#ffffff", "#e8e8e8"
        sel = COLOR_PRIMARY
    style.configure("Maxsub.Treeview", background=bg, foreground=fg, fieldbackground=field_bg,
                     rowheight=26, borderwidth=0, font=("Segoe UI", 10))
    style.map("Maxsub.Treeview", background=[("selected", sel)], foreground=[("selected", "#ffffff")])
    style.configure("Maxsub.Treeview.Heading", background=head_bg, foreground=fg,
                     borderwidth=1, font=("Segoe UI", 10, "bold"))
    style.map("Maxsub.Treeview.Heading", background=[("active", sel)])


class EditorPanel(ctk.CTkFrame):
    def __init__(self, master, on_select=None, on_change=None, on_request_seek=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_select = on_select          # callback(SubtitleLine)
        self.on_change = on_change          # callback() -> dipanggil tiap kali data berubah
        self.on_request_seek = on_request_seek  # callback(ms) -> minta video/waveform pindah posisi
        self.lines = []
        self.current_line = None
        self._row_to_line = {}
        self._suppress = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._build_tree()
        self._build_edit_box()

    # ------------------------------------------------------------------ tree
    def _build_tree(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, columns=COLUMNS, show="headings",
                                  selectmode="browse", style="Maxsub.Treeview")
        for col in COLUMNS:
            self.tree.heading(col, text=HEADINGS[col])
            anchor = "center" if col in ("no", "mulai", "selesai", "durasi") else "w"
            self.tree.column(col, width=WIDTHS[col], anchor=anchor)
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ctk.CTkButton(toolbar, text="+ Baris Baru", width=100, command=self._add_line).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="Duplikat", width=85, command=self._duplicate_line).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="Gabung", width=85, command=self._merge_next).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="Pisah", width=70, command=self._split_current).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="Hapus", width=70, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
                      command=self._delete_line).pack(side="left", padx=2)
        self.count_label = ctk.CTkLabel(toolbar, text="0 baris", font=ctk.CTkFont(size=11),
                                         text_color=("gray40", "gray60"))
        self.count_label.pack(side="right", padx=6)

    # --------------------------------------------------------------- editbox
    def _build_edit_box(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        time_row = ctk.CTkFrame(frame, fg_color="transparent")
        time_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 4))
        ctk.CTkLabel(time_row, text="Mulai").pack(side="left")
        self.start_entry = ctk.CTkEntry(time_row, width=95, placeholder_text="00:00:00,000")
        self.start_entry.pack(side="left", padx=(4, 14))
        self.start_entry.bind("<Return>", self._on_time_edit)
        self.start_entry.bind("<FocusOut>", self._on_time_edit)
        ctk.CTkLabel(time_row, text="Selesai").pack(side="left")
        self.end_entry = ctk.CTkEntry(time_row, width=95, placeholder_text="00:00:00,000")
        self.end_entry.pack(side="left", padx=(4, 8))
        self.end_entry.bind("<Return>", self._on_time_edit)
        self.end_entry.bind("<FocusOut>", self._on_time_edit)
        ctk.CTkButton(time_row, text="\u25B6 Preview", width=95,
                      command=lambda: self._seek_to(is_start=True)).pack(side="left", padx=1)

        ctk.CTkLabel(frame, text="Teks Asli", font=ctk.CTkFont(size=11),
                     text_color=("gray40", "gray60")).grid(row=1, column=0, sticky="w", padx=8, pady=(6, 0))
        self.text_box = ctk.CTkTextbox(frame, height=90, wrap="word")
        self.text_box.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 4))
        self.text_box.bind("<KeyRelease>", self._on_text_edit)

        ctk.CTkLabel(frame, text="Terjemahan", font=ctk.CTkFont(size=11),
                     text_color=("gray40", "gray60")).grid(row=3, column=0, sticky="w", padx=8, pady=(4, 0))
        self.translated_box = ctk.CTkTextbox(frame, height=90, wrap="word")
        self.translated_box.grid(row=4, column=0, sticky="nsew", padx=8, pady=(2, 10))
        self.translated_box.bind("<KeyRelease>", self._on_translated_edit)

        self._set_edit_enabled(False)

    def _set_edit_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for w in (self.start_entry, self.end_entry, self.text_box, self.translated_box):
            w.configure(state=state)

    # ------------------------------------------------------------- refresh
    def refresh(self, lines):
        self.lines = list(lines)
        self._suppress = True
        selected_line = self.current_line
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._row_to_line = {}
        for line in self.lines:
            row_id = self.tree.insert("", "end", values=(
                line.index, ms_to_short_time(line.start_ms), ms_to_short_time(line.end_ms),
                f"{line.duration_ms / 1000:.1f}s",
                line.text.replace("\n", "  /  "), line.translated_text.replace("\n", "  /  "),
            ))
            self._row_to_line[row_id] = line
        self.count_label.configure(text=f"{len(self.lines)} baris")
        self._suppress = False
        if selected_line in self.lines:
            self.select_line(selected_line, notify=False)
        elif self.lines:
            pass
        else:
            self.current_line = None
            self._set_edit_enabled(False)

    def refresh_row(self, line: SubtitleLine):
        """Update satu baris di tree tanpa membangun ulang seluruh grid (dipakai
        saat drag di waveform mengubah waktu, supaya tidak flicker/lag)."""
        for row_id, l in self._row_to_line.items():
            if l is line:
                self.tree.item(row_id, values=(
                    line.index, ms_to_short_time(line.start_ms), ms_to_short_time(line.end_ms),
                    f"{line.duration_ms / 1000:.1f}s",
                    line.text.replace("\n", "  /  "), line.translated_text.replace("\n", "  /  "),
                ))
                break
        if self.current_line is line:
            self._suppress = True
            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, line.start_srt)
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, line.end_srt)
            self._suppress = False

    def select_line(self, line, notify: bool = True):
        for row_id, l in self._row_to_line.items():
            if l is line:
                self.tree.selection_set(row_id)
                self.tree.see(row_id)
                break
        self._load_into_editbox(line, notify=notify)

    def _load_into_editbox(self, line, notify: bool = True):
        self.current_line = line
        self._suppress = True
        self._set_edit_enabled(line is not None)
        if line is not None:
            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, line.start_srt)
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, line.end_srt)
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", line.text)
            self.translated_box.delete("1.0", "end")
            self.translated_box.insert("1.0", line.translated_text)
        else:
            self.start_entry.delete(0, "end")
            self.end_entry.delete(0, "end")
            self.text_box.delete("1.0", "end")
            self.translated_box.delete("1.0", "end")
        self._suppress = False
        if notify and self.on_select and line is not None:
            self.on_select(line)

    # ------------------------------------------------------------- events
    def _on_tree_select(self, _event=None):
        if self._suppress:
            return
        sel = self.tree.selection()
        if not sel:
            return
        line = self._row_to_line.get(sel[0])
        if line is not None:
            self._load_into_editbox(line, notify=True)

    def _on_tree_double_click(self, _event=None):
        if self.current_line and self.on_request_seek:
            self.on_request_seek(self.current_line.start_ms)

    def _seek_to(self, is_start=True):
        if self.current_line and self.on_request_seek:
            ms = self.current_line.start_ms if is_start else self.current_line.end_ms
            self.on_request_seek(ms)

    def _on_time_edit(self, _event=None):
        if self._suppress or self.current_line is None:
            return
        start_ms = parse_flexible_time(self.start_entry.get())
        end_ms = parse_flexible_time(self.end_entry.get())
        changed = False
        if start_ms is not None and start_ms != self.current_line.start_ms:
            self.current_line.start_ms = max(0, start_ms)
            changed = True
        if end_ms is not None and end_ms != self.current_line.end_ms:
            self.current_line.end_ms = max(self.current_line.start_ms + 50, end_ms)
            changed = True
        if changed:
            self.refresh_row(self.current_line)
            if self.on_change:
                self.on_change()

    def _on_text_edit(self, _event=None):
        if self._suppress or self.current_line is None:
            return
        self.current_line.text = self.text_box.get("1.0", "end-1c")
        self.refresh_row(self.current_line)
        if self.on_change:
            self.on_change()

    def _on_translated_edit(self, _event=None):
        if self._suppress or self.current_line is None:
            return
        self.current_line.translated_text = self.translated_box.get("1.0", "end-1c")
        self.refresh_row(self.current_line)
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------- actions
    def _add_line(self):
        if self.on_change:
            self.on_change("add_line")

    def _duplicate_line(self):
        if self.current_line and self.on_change:
            self.on_change("duplicate_line")

    def _merge_next(self):
        if self.current_line and self.on_change:
            self.on_change("merge_next")

    def _split_current(self):
        if self.current_line and self.on_change:
            self.on_change("split_current")

    def _delete_line(self):
        if self.current_line and self.on_change:
            self.on_change("delete_line")
