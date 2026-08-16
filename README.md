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

- **Tampilan profesional**: palet warna deep corporate blue + teal, font
  Segoe UI native Windows, dan indikator status bertitik warna (hijau=siap,
  teal=sedang proses, merah=gagal) di footer.
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
- **Gaya Subtitle**: atur font (pilihan font umum + font bawaan aplikasi),
  ukuran, tebal/tidak, warna teks & outline, dan **posisi vertikal** yang
  bisa digeser bebas dari bawah ke atas - berguna untuk menghindari
  tabrakan dengan logo/lower-third yang sudah ada di video broadcast.
  Berlaku konsisten baik di preview langsung maupun hasil export
  (burn-in), dan pengaturan tersimpan otomatis untuk sesi berikutnya.
- **Import**: video (mp4, mkv, avi, mov, webm, flv, ts, m4v, wmv), audio
  (mp3, wav, m4a, flac, aac, ogg, wma), subtitle (srt, vtt).
- **Export**: SRT, VTT, ASS/SSA, TXT, dan SRT dwibahasa (asli + terjemahan).
- **Export Video**: hasilkan file video jadi, bukan cuma file subtitle -
  pilih mode **Burn-in (Hardsub)** yang membakar subtitle permanen ke
  frame video (cocok untuk dibagikan ke media sosial, semua orang pasti
  bisa lihat subtitle-nya), atau **Sisip Track (Softsub)** yang menanam
  subtitle sebagai track terpisah dalam MKV/MP4 - proses jauh lebih
  cepat (tanpa render ulang), subtitle bisa dinyalakan/dimatikan atau
  diganti bahasanya langsung di pemutar video, bahkan bisa menyertakan
  track asli DAN terjemahan sekaligus supaya penonton bisa pilih sendiri.
- **Gabung Video + SRT**: tool mandiri untuk kasus video dan file subtitle
  yang sudah jadi dari sumber lain (bukan hasil transkripsi di aplikasi
  ini) - tinggal pilih video, pilih file SRT/VTT, langsung gabung jadi
  satu video (burn-in atau sisip track). Tidak perlu buka proyek/editor
  penuh sama sekali.
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
5. **Atur Gaya Subtitle** (opsional) — klik tombol **Gaya...** di sebelah
   checkbox "Overlay subtitle" untuk atur font, ukuran, warna, dan
   **posisi vertikal** (geser ke atas kalau bagian bawah video sudah ada
   logo/lower-third). Perubahan langsung terlihat di preview.
6. **Simpan/Export** — tombol **Simpan** cepat export SRT, atau pakai
   dropdown **Export** untuk pilih format lain / mode dwibahasa.
7. **Export Video** — kalau butuh file video jadi (bukan cuma file
   subtitle), klik tombol **Export Video...** (ungu, di sebelah dropdown
   Export). Pilih mode:
   - **Burn-in** kalau mau subtitle pasti kelihatan di mana saja tanpa
     tergantung pemutar video (misal untuk upload ke media sosial) —
     tapi video di-render ulang penuh, jadi butuh waktu. Gaya subtitle
     yang diatur di langkah 5 ikut terpakai di sini.
   - **Sisip Track** kalau mau proses cepat dan penonton bisa
     nyala/matikan subtitle sendiri (butuh pemutar yang mendukung,
     seperti VLC) — bisa sertakan track asli & terjemahan sekaligus.
8. **Proses Batch** — untuk banyak video sekaligus tanpa perlu ditunggu
   satu-satu.
9. **Gabung Video + SRT** — kalau Anda sudah punya video DAN file subtitle
   siap pakai dari luar (bukan mau transkripsi/terjemahan di sini), klik
   tombol ungu **"Gabung Video + SRT..."** di baris ketiga toolbar. Ini
   jalan pintas berdiri sendiri: pilih video → pilih file SRT/VTT → pilih
   mode (Burn-in/Sisip Track) → simpan. Tidak menyentuh proyek yang
   sedang terbuka di editor sama sekali.

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

**"Library cublas64_12.dll is not found or cannot be loaded" (atau pesan mirip)**
Ini artinya GPU NVIDIA Anda terdeteksi ada, tapi library CUDA (cuBLAS/
cuDNN) belum terpasang di sistem — umum terjadi kalau cuma driver GPU
biasa yang ter-install, bukan CUDA lengkap. MaxSubtitle otomatis
mendeteksi kegagalan tersebut dan langsung mengulang prosesnya memakai
CPU tanpa perlu tindakan apa pun dari Anda — cukup tunggu, transkripsi
akan tetap selesai (hanya sedikit lebih lambat karena berjalan di CPU).
Kalau ingin GPU benar-benar dipakai (jauh lebih cepat), ikuti
**TUTORIAL_INSTALL_CUDA.md** — cara paling gampang cuma satu baris
`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` tanpa perlu install
CUDA Toolkit besar dari NVIDIA. Jalankan `python cek_gpu.py` untuk
verifikasi status GPU Anda kapan saja.

**Export Video (burn-in) sangat lambat**
Ini normal — mode burn-in me-render ulang seluruh video dari awal (proses
paling berat di aplikasi ini). Untuk video panjang (siaran/broadcast durasi
puluhan menit), pertimbangkan pakai kualitas **Cepat**, atau pakai mode
**Sisip Track** sebagai gantinya kalau pemutar video penonton mendukung
subtitle track (jauh lebih cepat karena tidak render ulang).

**Export Video gagal dengan pesan soal audio/codec**
Coba lagi (mode burn-in otomatis mencoba ulang dengan audio di-encode
ulang ke AAC kalau "copy" gagal). Untuk mode Sisip Track, coba ganti
format output ke **MKV** — mendukung lebih banyak jenis codec video/audio
dibanding MP4 tanpa perlu re-encode.

**Subtitle di video hasil Sisip Track tidak muncul di pemutar saya**
Beberapa pemutar (termasuk sebagian pemutar bawaan Windows/ponsel) tidak
otomatis menyalakan track subtitle atau tidak mendukung format `mov_text`
di MP4. Coba buka dengan **VLC** (mendukung penuh), atau gunakan format
output **MKV** yang dukungannya lebih luas. Kalau tetap butuh subtitle
pasti tampil di semua pemutar, pakai mode **Burn-in** saja.

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
├── cek_gpu.py                 Script diagnostik status GPU/CUDA
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
│   │   ├── translator.py      Wrapper Google Translate
│   │   ├── subtitle_style.py  Model gaya (font/warna/posisi) + render bersama
│   │   └── video_export.py    Export video burn-in (hardsub) & sisip track (softsub)
│   ├── ui/                    Komponen GUI (customtkinter)
│   │   ├── main_window.py     Jendela utama, orkestrasi semua panel
│   │   ├── toolbar.py         Toolbar aksi
│   │   ├── editor_panel.py    Grid subtitle + panel edit
│   │   ├── video_panel.py     Preview video + overlay subtitle
│   │   ├── waveform_panel.py  Visualisasi waveform interaktif
│   │   ├── settings_dialog.py Dialog pengaturan
│   │   ├── batch_dialog.py    Dialog proses batch
│   │   ├── video_export_dialog.py  Dialog export video (burn-in/sisip track)
│   │   ├── quick_merge_dialog.py   Dialog mandiri gabung video + SRT eksternal
│   │   ├── subtitle_style_dialog.py Dialog atur gaya subtitle (font/warna/posisi)
│   │   └── footer.py          Status bar + watermark
│   └── utils/
│       ├── config.py          Penyimpanan pengaturan pengguna
│       └── constants.py       Konstanta aplikasi
├── assets/
│   ├── icon.ico                 Ikon aplikasi
│   ├── fonts/NotoSans-Bold.ttf   Font untuk overlay subtitle
│   └── themes/professional.json  Tema warna kustom (deep blue + teal)
├── tests/test_core.py         Unit test logika inti
└── .github/workflows/         Workflow build otomatis cloud
```

---

*MaxSubtitle dibuat dan dikembangkan oleh iman.mn_*
