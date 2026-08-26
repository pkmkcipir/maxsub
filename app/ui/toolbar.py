"""Toolbar atas, disusun 3 baris: (1) file & export, (2) proses AI, (3) alat bantu."""
import customtkinter as ctk

from ..utils.constants import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SECONDARY, COLOR_SECONDARY_HOVER,
    COLOR_DANGER, COLOR_DANGER_HOVER,
)


class Toolbar(ctk.CTkFrame):
    def __init__(self, master, callbacks: dict, **kwargs):
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.callbacks = callbacks
        self._build()

    def _btn(self, parent, text, key, width=110, **extra):
        return ctk.CTkButton(
            parent, text=text, width=width,
            command=self.callbacks.get(key, lambda: None), **extra,
        )

    def _build(self):
        # --- baris 1: operasi file ---
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(8, 4))

        left = ctk.CTkFrame(row1, fg_color="transparent")
        left.pack(side="left")
        self._btn(left, "Buka Video/Audio", "open_media", width=155).pack(side="left", padx=3)
        self._btn(left, "Buka Subtitle", "open_subtitle", width=125).pack(side="left", padx=3)
        self._btn(left, "Simpan", "save", width=90).pack(side="left", padx=3)

        export_menu_btn = ctk.CTkOptionMenu(
            left, values=["Export SRT", "Export VTT", "Export ASS", "Export TXT", "Export SRT Dwibahasa"],
            command=self._on_export_selected, width=165,
        )
        export_menu_btn.set("Export...")
        export_menu_btn.pack(side="left", padx=3)
        self.export_menu_btn = export_menu_btn

        self._btn(left, "Export Video...", "export_video", width=130).pack(side="left", padx=3)

        right1 = ctk.CTkFrame(row1, fg_color="transparent")
        right1.pack(side="right")
        self._btn(right1, "Pengaturan", "settings", width=105).pack(side="left", padx=3)
        self._btn(right1, "Tentang", "about", width=90).pack(side="left", padx=3)

        # --- baris 2: proses AI ---
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0, 8))

        self.auto_btn = self._btn(row2, "Proses Otomatis", "auto_process", width=155,
                                   fg_color=COLOR_SECONDARY, hover_color=COLOR_SECONDARY_HOVER,
                                   font=ctk.CTkFont(weight="bold"))
        self.auto_btn.pack(side="left", padx=3)
        self.transcribe_btn = self._btn(row2, "Transkripsi", "transcribe", width=110)
        self.transcribe_btn.pack(side="left", padx=3)
        self.translate_btn = self._btn(row2, "Terjemahkan", "translate", width=110)
        self.translate_btn.pack(side="left", padx=3)
        self.cancel_btn = self._btn(row2, "Batal", "cancel", width=80,
                                     fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER)
        self.cancel_btn.pack(side="left", padx=3)
        self.cancel_btn.configure(state="disabled")
        self._busy_exclusive_widgets = [self.auto_btn, self.transcribe_btn, self.translate_btn]

        # --- baris 3: alat bantu (batch, gabung video+srt) ---
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(0, 8))
        self._btn(row3, "Proses Batch", "batch", width=115).pack(side="left", padx=3)
        self._btn(row3, "Gabung Video + SRT...", "quick_merge", width=165).pack(side="left", padx=3)

    def _on_export_selected(self, choice: str):
        mapping = {
            "Export SRT": "export_srt",
            "Export VTT": "export_vtt",
            "Export ASS": "export_ass",
            "Export TXT": "export_txt",
            "Export SRT Dwibahasa": "export_srt_bilingual",
        }
        key = mapping.get(choice)
        if key and key in self.callbacks:
            self.callbacks[key]()
        self.export_menu_btn.set("Export...")

    def set_busy(self, busy: bool):
        """Nonaktifkan tombol berat saat proses AI berjalan supaya user tidak
        memicu proses tumpang-tindih. Tombol Batal justru diaktifkan saat busy."""
        state = "disabled" if busy else "normal"
        for child in self.winfo_children():
            self._set_state_recursive(child, state)
        self.cancel_btn.configure(state=("normal" if busy else "disabled"))

    def _set_state_recursive(self, widget, state):
        if isinstance(widget, (ctk.CTkButton, ctk.CTkOptionMenu)):
            try:
                widget.configure(state=state)
            except Exception:
                pass
        for child in widget.winfo_children():
            self._set_state_recursive(child, state)
