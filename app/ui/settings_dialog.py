"""Dialog pengaturan: model Whisper, perangkat (CPU/GPU), bahasa, tema."""
import customtkinter as ctk

from ..core.video_utils import check_ffmpeg_available
from ..utils.constants import (
    WHISPER_MODELS, WHISPER_MODEL_LABELS, DEVICE_OPTIONS, DEVICE_LABELS,
    LANGUAGES, TARGET_LANGUAGES, COLOR_DANGER,
)


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, config_manager, on_save=None):
        super().__init__(master)
        self.config_manager = config_manager
        self.on_save = on_save

        self.title("Pengaturan - MaxSubtitle")
        self.geometry("480x700")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build()
        self.after(50, self._center_on_parent)

    def _center_on_parent(self):
        self.update_idletasks()
        try:
            px = self.master.winfo_rootx()
            py = self.master.winfo_rooty()
            pw = self.master.winfo_width()
            ph = self.master.winfo_height()
            w, h = 480, 700
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    def _build(self):
        pad = {"padx": 20, "pady": (12, 4)}
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(container, text="Model Transkripsi (Whisper)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.model_menu = ctk.CTkOptionMenu(
            container, values=[WHISPER_MODEL_LABELS[m] for m in WHISPER_MODELS], width=420)
        current_model = self.config_manager.get("model_size")
        self.model_menu.set(WHISPER_MODEL_LABELS.get(current_model, WHISPER_MODEL_LABELS["small"]))
        self.model_menu.pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkLabel(container, text="Model lebih besar = lebih akurat tapi lebih lambat & butuh RAM lebih.",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     wraplength=420, justify="left").pack(anchor="w", padx=20)

        ctk.CTkLabel(container, text="Perangkat Pemrosesan",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.device_menu = ctk.CTkOptionMenu(
            container, values=[DEVICE_LABELS[d] for d in DEVICE_OPTIONS], width=420)
        current_device = self.config_manager.get("device")
        self.device_menu.set(DEVICE_LABELS.get(current_device, DEVICE_LABELS["auto"]))
        self.device_menu.pack(anchor="w", padx=20, pady=(0, 4))

        ctk.CTkLabel(container, text="Bahasa Sumber (Video/Audio)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.source_lang_menu = ctk.CTkOptionMenu(
            container, values=list(LANGUAGES.values()), width=420)
        current_source = self.config_manager.get("source_language")
        self.source_lang_menu.set(LANGUAGES.get(current_source, LANGUAGES["auto"]))
        self.source_lang_menu.pack(anchor="w", padx=20, pady=(0, 4))

        ctk.CTkLabel(container, text="Bahasa Target (Terjemahan)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.target_lang_menu = ctk.CTkOptionMenu(
            container, values=list(TARGET_LANGUAGES.values()), width=420)
        current_target = self.config_manager.get("target_language")
        self.target_lang_menu.set(TARGET_LANGUAGES.get(current_target, TARGET_LANGUAGES["id"]))
        self.target_lang_menu.pack(anchor="w", padx=20, pady=(0, 4))

        ctk.CTkLabel(container, text="Terjemahan Tanpa Limit (LibreTranslate Lokal)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self.libre_switch_var = ctk.BooleanVar(value=self.config_manager.get("use_libretranslate", False))
        self.libre_switch = ctk.CTkSwitch(
            container, text="Pakai server LibreTranslate lokal (gratis & tanpa limit harian)",
            variable=self.libre_switch_var, onvalue=True, offvalue=False,
            command=self._toggle_libre_fields)
        self.libre_switch.pack(anchor="w", padx=20, pady=(0, 6))

        self.libre_url_entry = ctk.CTkEntry(container, width=420, placeholder_text="http://localhost:5000/")
        self.libre_url_entry.insert(0, self.config_manager.get("libretranslate_url", "http://localhost:5000/"))
        self.libre_url_entry.pack(anchor="w", padx=20, pady=(0, 4))

        self.libre_key_entry = ctk.CTkEntry(
            container, width=420,
            placeholder_text="API key (kosongkan kalau server tidak pakai --api-keys)")
        self.libre_key_entry.insert(0, self.config_manager.get("libretranslate_api_key", ""))
        self.libre_key_entry.pack(anchor="w", padx=20, pady=(0, 4))

        ctk.CTkLabel(container,
                     text=("Butuh server LibreTranslate menyala di komputer sendiri "
                           "(pip install libretranslate lalu jalankan perintah 'libretranslate', "
                           "atau via Docker) - lihat README bagian \"Terjemahan tanpa limit\". "
                           "Kalau server ini tidak menyala, MaxSubtitle otomatis memakai Google/"
                           "MyMemory spt biasa, jadi aman diaktifkan lebih dulu sebelum servernya siap."),
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                     wraplength=420, justify="left").pack(anchor="w", padx=20, pady=(0, 4))
        self._toggle_libre_fields()

        ctk.CTkLabel(container, text="Tema Tampilan",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        theme_labels = {"dark": "Gelap", "light": "Terang", "system": "Ikuti Sistem"}
        self.theme_menu = ctk.CTkOptionMenu(container, values=list(theme_labels.values()), width=420)
        current_theme = self.config_manager.get("theme")
        self.theme_menu.set(theme_labels.get(current_theme, "Gelap"))
        self.theme_menu.pack(anchor="w", padx=20, pady=(0, 4))
        self._theme_labels = theme_labels

        ctk.CTkLabel(container, text="Status Sistem",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        ffmpeg_ok = check_ffmpeg_available()
        ffmpeg_text = "[OK] ffmpeg terdeteksi" if ffmpeg_ok else "[TIDAK ADA] ffmpeg tidak ditemukan - transkripsi video tidak akan berjalan"
        ffmpeg_color = ("gray20", "gray80") if ffmpeg_ok else COLOR_DANGER
        ctk.CTkLabel(container, text=ffmpeg_text, text_color=ffmpeg_color,
                     wraplength=420, justify="left").pack(anchor="w", padx=20, pady=(0, 2))

        from ..core.transcriber import gpu_available
        gpu_ok = gpu_available()
        gpu_text = ("[OK] GPU NVIDIA terdeteksi (dipakai otomatis kalau library CUDA "
                    "lengkap; kalau tidak, otomatis fallback ke CPU tanpa perlu diatur manual)"
                    if gpu_ok else "GPU tidak terdeteksi - akan memakai CPU")
        ctk.CTkLabel(container, text=gpu_text,
                     wraplength=420, justify="left").pack(anchor="w", padx=20, pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(btn_row, text="Batal", width=100, fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_row, text="Simpan", width=100, command=self._save).pack(side="right")

    def _toggle_libre_fields(self):
        state = "normal" if self.libre_switch_var.get() else "disabled"
        self.libre_url_entry.configure(state=state)
        self.libre_key_entry.configure(state=state)

    def _save(self):
        rev_model = {v: k for k, v in WHISPER_MODEL_LABELS.items()}
        rev_device = {v: k for k, v in DEVICE_LABELS.items()}
        rev_lang = {v: k for k, v in LANGUAGES.items()}
        rev_target = {v: k for k, v in TARGET_LANGUAGES.items()}
        rev_theme = {v: k for k, v in self._theme_labels.items()}

        self.config_manager.set("model_size", rev_model.get(self.model_menu.get(), "small"))
        self.config_manager.set("device", rev_device.get(self.device_menu.get(), "auto"))
        self.config_manager.set("source_language", rev_lang.get(self.source_lang_menu.get(), "auto"))
        self.config_manager.set("target_language", rev_target.get(self.target_lang_menu.get(), "id"))
        self.config_manager.set("use_libretranslate", bool(self.libre_switch_var.get()))
        libre_url = self.libre_url_entry.get().strip() or "http://localhost:5000/"
        self.config_manager.set("libretranslate_url", libre_url)
        self.config_manager.set("libretranslate_api_key", self.libre_key_entry.get().strip())
        new_theme = rev_theme.get(self.theme_menu.get(), "dark")
        self.config_manager.set("theme", new_theme)
        self.config_manager.save()

        if self.on_save:
            self.on_save()
        self.destroy()
