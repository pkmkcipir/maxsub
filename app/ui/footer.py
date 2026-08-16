"""Footer: status singkat + indikator titik warna di kiri, watermark copyright
di kanan (selalu tampil)."""
import customtkinter as ctk

from ..utils.constants import APP_VERSION, COPYRIGHT_WATERMARK, COLOR_SECONDARY, COLOR_DANGER

STATUS_DOT_COLORS = {
    "idle": "#3FB950",           # hijau - siap/normal (konvensi umum: hijau = OK)
    "active": COLOR_SECONDARY,   # teal - sedang memproses
    "error": COLOR_DANGER,       # merah - gagal/error
}
_ACTIVE_KEYWORDS = ("...", "memuat", "menerjemahkan", "transkripsi", "membakar",
                    "menyisipkan", "memproses", "mengekstrak", "membatalkan")
_ERROR_KEYWORDS = ("gagal", "error")


class Footer(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("height", 28)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=0, column=0, sticky="w", padx=10, pady=3)

        self.status_dot = ctk.CTkLabel(status_frame, text="\u25CF", width=10,
                                        font=ctk.CTkFont(size=11),
                                        text_color=STATUS_DOT_COLORS["idle"])
        self.status_dot.pack(side="left", padx=(0, 4))

        self.status_label = ctk.CTkLabel(status_frame, text="Siap.", anchor="w",
                                          font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self, height=8)
        self.progress_bar.set(0)
        # progress bar disisipkan di tengah, disembunyikan sampai dibutuhkan
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=10, pady=3)
        self.progress_bar.grid_remove()

        version_label = ctk.CTkLabel(self, text=f"v{APP_VERSION}", anchor="e",
                                      font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"))
        version_label.grid(row=0, column=2, sticky="e", padx=(10, 4), pady=3)

        watermark = ctk.CTkLabel(self, text=COPYRIGHT_WATERMARK, anchor="e",
                                  font=ctk.CTkFont(size=11, weight="bold"),
                                  text_color=("gray35", "gray65"))
        watermark.grid(row=0, column=3, sticky="e", padx=(4, 10), pady=3)

    def set_status(self, text: str, status_type: str = None):
        """status_type opsional: 'idle' (hijau) / 'active' (teal) / 'error' (merah).
        Kalau tidak diisi (semua pemanggilan lama di seluruh aplikasi), warnanya
        otomatis ditebak dari kata kunci umum di teks - jadi seluruh kode yang
        sudah ada TIDAK PERLU diubah sama sekali, titik status tetap relevan
        sebagai bonus visual murni."""
        self.status_label.configure(text=text)
        if status_type is None:
            lower = text.lower()
            if any(k in lower for k in _ERROR_KEYWORDS):
                status_type = "error"
            elif any(k in lower for k in _ACTIVE_KEYWORDS):
                status_type = "active"
            else:
                status_type = "idle"
        self.status_dot.configure(text_color=STATUS_DOT_COLORS.get(status_type, STATUS_DOT_COLORS["idle"]))

    def set_progress(self, fraction: float):
        """fraction: 0..1. Sembunyikan progress bar kalau None."""
        if fraction is None:
            self.progress_bar.grid_remove()
            return
        self.progress_bar.grid()
        self.progress_bar.set(max(0.0, min(1.0, fraction)))
