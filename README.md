# MaxSubtitle 2.0

Aplikasi desktop Windows untuk transkripsi dan terjemahan subtitle video secara
otomatis berbasis AI (faster-whisper + Google Translate), dengan editor
subtitle bergaya SubtitleEdit: grid editor, waveform, preview video dengan
overlay subtitle langsung, dan export multi-format.

**Copyright (c) iman.mn_**

---

## Daftar Isi

1. [Fitur](#fitur)
2. [Yang Tidak Termasuk (Batasan)](#yang-tidak-termasuk-batasan)
3. [Prasyarat](#prasyarat)
4. [Cara Menjalankan (Mode Development)](#cara-menjalankan-mode-development)
5. [Cara Build Jadi .exe](#cara-build-jadi-exe)
6. [Cara Membuat Installer Windows](#cara-membuat-installer-windows)
7. [Build Otomatis via GitHub Actions (Cloud)](#build-otomatis-via-github-actions-cloud)
8. [Panduan Penggunaan](#panduan-penggunaan)
9. [Troubleshooting](#troubleshooting)
10. [Struktur Proyek](#struktur-proyek)

---

## Fitur

- **Proses Otomatis 1-klik**: video/audio masuk, subtitle hasil transkripsi +
  terjemahan langsung keluar.
- **Transkripsi AI (faster-whisper)**: 5 pilihan model (tiny s/d large-v3),
  auto-deteksi GPU NVIDIA dengan fallback otomatis ke CPU jika GPU/driver
  bermasalah.
- **Auto-translate** ke ~18 bahasa (default Indonesia) via Google Translate,
  dengan retry otomatis jika kena rate limit.
- **Editor grid subtitle**: tambah, hapus, duplikat, gabung, pisah baris;
  edit teks asli & terjemahan berdampingan.
- **Waveform interaktif**: klik untuk pindah posisi, drag tepi kiri/kanan
  kotak subtitle terpilih untuk mengubah waktu mulai/selesai secara visual.
- **Preview video**: play/pause/seek dengan overlay subtitle real-time
  langsung di atas video (bisa dimatikan).
- **Import**: video (mp4, mkv, avi, mov, webm, flv, ts, m4v, wmv), audio
  (mp3, wav, m4a, flac, aac, ogg, wma), subtitle (srt, vtt).
- **Export**: SRT, VTT, ASS/SSA, TXT, dan SRT dwibahasa (asli + terjemahan).
- **Proses Batch**: antre banyak video sekaligus, diproses otomatis tanpa
  dijaga, hasil SRT langsung tersimpan per file.
- **Tema gelap/terang**, pengaturan tersimpan otomatis antar sesi.
- **Watermark** "@copyright iman.mn_" di footer aplikasi.

## Yang Tidak Termasuk (Batasan)

Supaya ekspektasi jelas — MaxSubtitle terinspirasi SubtitleEdit tapi bukan
kloning 1:1 (SubtitleEdit adalah proyek C#/.NET yang dikembangkan 15+ tahun).
Yang **belum** ada di versi ini:

- OCR untuk subtitle berbasis gambar (VobSub/PGS/subtitle DVD)
- Editor efek/style ASS tingkat lanjut (karaoke, animasi typewriter)
- Kolaborasi jaringan / sinkronisasi cloud
- Sistem plugin
- Video player frame-accurate broadcast-grade (preview di sini best-effort,
  sinkron audio-video berbasis estimasi waktu, bukan clock frame-exact)
- Spell-checker bawaan
- Drag-and-drop file ke jendela aplikasi (gunakan tombol "Buka Video/Audio")

## Prasyarat

- **Windows 11** (atau Windows 10 64-bit)
- **Python 3.10 - 3.12** (64-bit) — unduh di https://www.python.org/downloads/
  Saat instalasi, **centang "Add python.exe to PATH"**.
- **ffmpeg** — dibutuhkan untuk membaca video/audio. Cara termudah:
  1. Unduh build Windows dari https://www.gyan.dev/ffmpeg/builds/ (pilih
     "release essentials")
  2. Ekstrak, lalu tambahkan folder `bin`-nya ke PATH Windows, **atau**
  3. Cukup salin `ffmpeg.exe` dan `ffprobe.exe` ke dalam folder
     `dist\MaxSubtitle\ffmpeg\` setelah build (aplikasi otomatis mendeteksi
     ffmpeg di folder itu lebih dulu sebelum mencari di PATH).
- (Opsional) **GPU NVIDIA + driver terbaru** untuk transkripsi lebih cepat.
  Tanpa GPU, aplikasi otomatis memakai CPU (lebih lambat tapi tetap jalan).
- (Opsional, untuk membuat installer) **Inno Setup 6** —
  https://jrsoftware.org/isdl.php

## Cara Menjalankan (Mode Development)

Untuk mencoba aplikasi tanpa build exe dulu:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Cara Build Jadi .exe

> **Penting**: proyek ini dibuat di lingkungan Linux, sehingga file .exe
> Windows **harus di-build di komputer Windows** (PyInstaller tidak bisa
> cross-compile Linux -> Windows). Semua source code sudah diuji secara
> menyeluruh di sisi logika/GUI, tinggal di-compile di mesin Windows Anda,
> atau pakai opsi cloud di bagian 7 kalau tidak mau install apa pun secara
> lokal.

Cara paling gampang — jalankan `build.bat` (double-click, atau lewat
Command Prompt):

```bat
build.bat
```

Script ini otomatis: membuat virtual environment, install semua dependency,
menjalankan self-test, lalu build exe dengan PyInstaller. Hasilnya ada di
`dist\MaxSubtitle\MaxSubtitle.exe` — folder ini portable, bisa di-zip dan
dipindah ke komputer Windows lain tanpa perlu install Python di sana.

Kalau mau manual step-by-step:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pyinstaller build.spec --noconfirm
```

## Cara Membuat Installer Windows

Setelah `dist\MaxSubtitle\` berhasil dibuat (langkah di atas):

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (gratis)
2. Buka `installer.iss` dengan Inno Setup Compiler
3. Tekan **F9** (atau menu Build > Compile)
4. Installer jadi ada di `installer_output\MaxSubtitle_Setup.exe`

Installer ini sudah termasuk: wizard instalasi standar Windows, pilihan
shortcut Desktop, entry di Start Menu, dan uninstaller resmi (muncul di
"Add or Remove Programs").

## Build Otomatis via GitHub Actions (Cloud)

Kalau tidak mau install Python/Inno Setup secara lokal, proyek ini sudah
dilengkapi workflow GitHub Actions (`.github/workflows/build-windows.yml`)
yang membangun exe + installer di komputer Windows milik GitHub, gratis
untuk repo publik (dan repo privat masih dapat jatah menit gratis bulanan):

1. Push folder proyek ini ke repository GitHub baru
2. Buka tab **Actions** di repo tersebut
3. Pilih workflow **"Build MaxSubtitle Windows Installer"**, klik
   **"Run workflow"**
4. Tunggu sekitar 10-15 menit
5. Unduh hasilnya di bagian **Artifacts** pada halaman run tersebut — ada
   dua paket: folder aplikasi portable, dan installer siap pakai

Workflow ini juga otomatis berjalan setiap kali Anda push tag versi
(misalnya `git tag v2.0.0 && git push --tags`).

## Panduan Penggunaan

1. **Buka Video/Audio** — pilih file video atau audio Anda. Aplikasi
   otomatis mengekstrak audio dan menyiapkan waveform.
2. **Proses Otomatis** — transkripsi + terjemahan berjalan sekaligus.
   Model & bahasa target bisa diatur lewat **Pengaturan**.
   (Atau pakai tombol **Transkripsi** dan **Terjemahkan** terpisah kalau
   mau kontrol lebih detail — misalnya transkrip dulu, edit teksnya, baru
   terjemahkan.)
3. **Edit hasil** — klik baris di tabel untuk membuka di panel edit kanan.
   Ubah teks/waktu langsung, atau drag tepi kotak subtitle di waveform.
4. **Cek dengan preview video** — klik dua kali baris (atau tombol
   "Preview") untuk lompat ke posisi itu di video.
5. **Simpan/Export** — tombol **Simpan** cepat export SRT, atau pakai
   dropdown **Export** untuk pilih format lain / mode dwibahasa.
6. **Proses Batch** — untuk banyak video sekaligus tanpa perlu ditunggu
   satu-satu.

Shortcut keyboard: `Ctrl+O` buka media, `Ctrl+S` simpan, `Spasi`
play/pause video (saat fokus bukan di kotak teks).

## Troubleshooting

**"ffmpeg tidak ditemukan"**
Pastikan ffmpeg ada di PATH, atau taruh `ffmpeg.exe` + `ffprobe.exe` di
folder `ffmpeg\` di sebelah `MaxSubtitle.exe`.

**Transkripsi lambat sekali**
Model besar (medium/large-v3) berat di CPU. Coba model `small` atau `base`
di Pengaturan, atau pakai GPU NVIDIA kalau tersedia.

**Terjemahan gagal / error rate limit**
Google Translate gratis kadang membatasi permintaan beruntun. Aplikasi
sudah otomatis retry, tapi kalau tetap gagal, tunggu beberapa menit dan
coba lagi, atau proses dalam batch lebih kecil.

**Video tidak muncul tapi audio jalan**
Beberapa format/codec video mungkin tidak didukung OpenCV. Coba convert
video ke mp4 (H.264) dulu dengan ffmpeg, atau gunakan mode audio-saja
(hasil transkripsi tetap jalan normal, hanya preview visual yang tidak ada).

**Build PyInstaller gagal / exe tidak mau jalan**
Jalankan `python main.py --selftest` dulu sebelum build — kalau ini juga
gagal, masalahnya ada di instalasi dependency, bukan di proses bundling.
Pastikan versi Python 64-bit dan 3.10-3.12.

**Model Whisper lama sekali diunduh saat pertama kali dipakai**
Model diunduh dari Hugging Face saat pertama kali dipilih (butuh internet).
Setelah itu tersimpan di cache lokal dan tidak perlu unduh ulang.

## Struktur Proyek

```
MaxSubtitle/
├── main.py                    Entry point aplikasi
├── build.spec                 Konfigurasi PyInstaller
├── build.bat                  Script build otomatis (Windows)
├── installer.iss              Script Inno Setup
├── requirements.txt           Daftar dependency Python
├── app/
│   ├── core/                  Logika inti (tanpa GUI)
│   │   ├── subtitle.py        Model data subtitle
│   │   ├── formats.py         Import/export SRT/VTT/ASS/TXT
│   │   ├── video_utils.py     Wrapper ffmpeg
│   │   ├── waveform.py        Generator data waveform
│   │   ├── audio_player.py    Pemutar audio dengan seek
│   │   ├── transcriber.py     Wrapper faster-whisper
│   │   └── translator.py      Wrapper Google Translate
│   ├── ui/                    Komponen GUI (customtkinter)
│   │   ├── main_window.py     Jendela utama, orkestrasi semua panel
│   │   ├── toolbar.py         Toolbar aksi
│   │   ├── editor_panel.py    Grid subtitle + panel edit
│   │   ├── video_panel.py     Preview video + overlay subtitle
│   │   ├── waveform_panel.py  Visualisasi waveform interaktif
│   │   ├── settings_dialog.py Dialog pengaturan
│   │   ├── batch_dialog.py    Dialog proses batch
│   │   └── footer.py          Status bar + watermark
│   └── utils/
│       ├── config.py          Penyimpanan pengaturan pengguna
│       └── constants.py       Konstanta aplikasi
├── assets/
│   ├── icon.ico                 Ikon aplikasi
│   └── fonts/NotoSans-Bold.ttf   Font untuk overlay subtitle
├── tests/test_core.py         Unit test logika inti
└── .github/workflows/         Workflow build otomatis cloud
```

---

*MaxSubtitle dibuat dan dikembangkan oleh iman.mn_*
