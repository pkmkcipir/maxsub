"""Dialog pengaturan gaya subtitle: font, ukuran, warna, posisi vertikal.

Perubahan langsung terlihat lewat callback on_change (biasanya terhubung ke
VideoPanel.set_subtitle_style, jadi preview di video ter-update real-time
sambil user menggeser slider/pilih warna)."""
from tkinter import colorchooser

import customtkinter as ctk

from ..core.subtitle_style import SubtitleStyle, FONT_CHOICES


class SubtitleStyleDialog(ctk.CTkToplevel):
    def __init__(self, master, style: SubtitleStyle, on_change=None, on_close=None):
        super().__init__(master)
        self.style = style.clone()
        self.on_change = on_change
        self.on_close = on_close

        self.title("Gaya Subtitle - MaxSubtitle")
        self.geometry("420x560")
        self.resizable(False, False)
        self.transient(master)

        self._build()
        self.after(50, self._center_on_parent)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _center_on_parent(self):
        self.update_idletasks()
        try:
            px, py = self.master.winfo_rootx(), self.master.winfo_rooty()
            pw, ph = self.master.winfo_width(), self.master.winfo_height()
            w, h = 420, 560
            x, y = px + (pw - w) // 2, py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    def _build(self):
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=4)
        pad = {"padx": 20, "pady": (10, 4)}

        # --- font ---
        ctk.CTkLabel(container, text="Font", font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(anchor="w", **pad)
        self.font_menu = ctk.CTkOptionMenu(container, values=list(FONT_CHOICES.keys()), width=360,
                                            command=self._on_font_change)
        self.font_menu.set(self.style.font_name)
        self.font_menu.pack(anchor="w", padx=20, pady=(0, 4))

        self.bold_var = ctk.BooleanVar(value=self.style.bold)
        ctk.CTkCheckBox(container, text="Tebal (Bold)", variable=self.bold_var,
                         command=self._on_change).pack(anchor="w", padx=20, pady=(2, 4))

        # --- ukuran font ---
        self.size_label_ref = ctk.CTkLabel(container, text=f"Ukuran Font: {self.style.font_size}px",
                                            font=ctk.CTkFont(size=13, weight="bold"))
        self.size_label_ref.pack(anchor="w", **pad)
        self.size_slider = ctk.CTkSlider(container, from_=16, to=96, number_of_steps=80,
                                          command=self._on_size_change, width=360)
        self.size_slider.set(self.style.font_size)
        self.size_slider.pack(anchor="w", padx=20, pady=(0, 4))

        # --- posisi vertikal ---
        self.position_label_ref = ctk.CTkLabel(
            container, text=f"Posisi Vertikal: {self.style.vertical_position}% dari bawah",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.position_label_ref.pack(anchor="w", **pad)
        pos_row = ctk.CTkFrame(container, fg_color="transparent")
        pos_row.pack(anchor="w", padx=20, fill="x")
        ctk.CTkLabel(pos_row, text="Bawah", font=ctk.CTkFont(size=10),
                     text_color=("gray40", "gray60")).pack(side="left")
        self.position_slider = ctk.CTkSlider(pos_row, from_=0, to=95, number_of_steps=95,
                                              command=self._on_position_change, width=290)
        self.position_slider.set(self.style.vertical_position)
        self.position_slider.pack(side="left", padx=6)
        ctk.CTkLabel(pos_row, text="Atas", font=ctk.CTkFont(size=10),
                     text_color=("gray40", "gray60")).pack(side="left")
        ctk.CTkLabel(container,
                     text="Geser untuk menghindari tabrakan dengan logo/lower-third yang\n"
                          "sudah ada di video.",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     justify="left").pack(anchor="w", padx=20, pady=(2, 4))

        # --- warna ---
        ctk.CTkLabel(container, text="Warna", font=ctk.CTkFont(size=13, weight="bold")
                     ).pack(anchor="w", **pad)
        color_row = ctk.CTkFrame(container, fg_color="transparent")
        color_row.pack(anchor="w", padx=20, fill="x", pady=(0, 4))

        text_col = ctk.CTkFrame(color_row, fg_color="transparent")
        text_col.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(text_col, text="Teks", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.text_color_btn = ctk.CTkButton(text_col, text="", width=60, height=28,
                                             fg_color=self.style.text_color,
                                             hover_color=self.style.text_color,
                                             border_width=1, border_color="gray50",
                                             command=self._pick_text_color)
        self.text_color_btn.pack(anchor="w", pady=(2, 0))

        outline_col = ctk.CTkFrame(color_row, fg_color="transparent")
        outline_col.pack(side="left")
        ctk.CTkLabel(outline_col, text="Outline", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.outline_color_btn = ctk.CTkButton(outline_col, text="", width=60, height=28,
                                                fg_color=self.style.outline_color,
                                                hover_color=self.style.outline_color,
                                                border_width=1, border_color="gray50",
                                                command=self._pick_outline_color)
        self.outline_color_btn.pack(anchor="w", pady=(2, 0))

        # --- ketebalan outline ---
        self.outline_label_ref = ctk.CTkLabel(container, text=f"Ketebalan Outline: {self.style.outline_width}px",
                                               font=ctk.CTkFont(size=13, weight="bold"))
        self.outline_label_ref.pack(anchor="w", **pad)
        self.outline_slider = ctk.CTkSlider(container, from_=0, to=6, number_of_steps=6,
                                             command=self._on_outline_change, width=360)
        self.outline_slider.set(self.style.outline_width)
        self.outline_slider.pack(anchor="w", padx=20, pady=(0, 8))

        # --- tombol ---
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(btn_row, text="Reset ke Default", fg_color="gray40", hover_color="gray30",
                      command=self._reset_default).pack(side="left")
        ctk.CTkButton(btn_row, text="Tutup", width=90, command=self._close).pack(side="right")

    # ------------------------------------------------------------- events
    def _on_font_change(self, _value=None):
        self.style.font_name = self.font_menu.get()
        self._on_change()

    def _on_size_change(self, value):
        self.style.font_size = int(value)
        self.size_label_ref.configure(text=f"Ukuran Font: {self.style.font_size}px")
        self._on_change()

    def _on_position_change(self, value):
        self.style.vertical_position = int(value)
        self.position_label_ref.configure(
            text=f"Posisi Vertikal: {self.style.vertical_position}% dari bawah")
        self._on_change()

    def _on_outline_change(self, value):
        self.style.outline_width = int(value)
        self.outline_label_ref.configure(text=f"Ketebalan Outline: {self.style.outline_width}px")
        self._on_change()

    def _pick_text_color(self):
        result = colorchooser.askcolor(color=self.style.text_color, title="Pilih warna teks",
                                        parent=self)
        if result and result[1]:
            self.style.text_color = result[1]
            self.text_color_btn.configure(fg_color=result[1], hover_color=result[1])
            self._on_change()

    def _pick_outline_color(self):
        result = colorchooser.askcolor(color=self.style.outline_color, title="Pilih warna outline",
                                        parent=self)
        if result and result[1]:
            self.style.outline_color = result[1]
            self.outline_color_btn.configure(fg_color=result[1], hover_color=result[1])
            self._on_change()

    def _reset_default(self):
        self.style = SubtitleStyle()
        self.font_menu.set(self.style.font_name)
        self.bold_var.set(self.style.bold)
        self.size_slider.set(self.style.font_size)
        self.size_label_ref.configure(text=f"Ukuran Font: {self.style.font_size}px")
        self.position_slider.set(self.style.vertical_position)
        self.position_label_ref.configure(
            text=f"Posisi Vertikal: {self.style.vertical_position}% dari bawah")
        self.outline_slider.set(self.style.outline_width)
        self.outline_label_ref.configure(text=f"Ketebalan Outline: {self.style.outline_width}px")
        self.text_color_btn.configure(fg_color=self.style.text_color, hover_color=self.style.text_color)
        self.outline_color_btn.configure(fg_color=self.style.outline_color,
                                          hover_color=self.style.outline_color)
        self._on_change()

    def _on_change(self):
        self.style.bold = self.bold_var.get()
        if self.on_change:
            self.on_change(self.style)

    def _close(self):
        if self.on_close:
            self.on_close(self.style)
        self.destroy()
