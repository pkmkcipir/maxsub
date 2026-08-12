"""Footer: status singkat di kiri + watermark copyright di kanan (selalu tampil)."""
import customtkinter as ctk

from ..utils.constants import APP_VERSION, COPYRIGHT_WATERMARK


class Footer(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("height", 28)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(self, text="Siap.", anchor="w",
                                          font=ctk.CTkFont(size=11))
        self.status_label.grid(row=0, column=0, sticky="w", padx=10, pady=3)

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

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def set_progress(self, fraction: float):
        """fraction: 0..1. Sembunyikan progress bar kalau None."""
        if fraction is None:
            self.progress_bar.grid_remove()
            return
        self.progress_bar.grid()
        self.progress_bar.set(max(0.0, min(1.0, fraction)))
