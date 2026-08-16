# Tutorial Lengkap: Pasang CUDA (cuBLAS/cuDNN) Supaya GPU Terdeteksi MaxSubtitle

Panduan ini untuk mengaktifkan transkripsi lewat **GPU NVIDIA** (jauh lebih
cepat dari CPU). Tanpa ini, MaxSubtitle tetap berjalan normal memakai CPU —
jadi ini bersifat **opsional**, murni untuk mempercepat proses.

Ada 2 metode. Saya rekomendasikan **Metode 1** untuk hampir semua orang.

---

## Sebelum Mulai — Cek Kelayakan GPU Anda

1. Buka Command Prompt, ketik `nvidia-smi`, tekan Enter.
   - Kalau muncul tabel info GPU → driver NVIDIA Anda sudah terpasang,
     lanjut ke bawah.
   - Kalau muncul "not recognized" → install driver dulu dari
     https://www.nvidia.com/download/index.aspx (pilih sesuai tipe GPU
     Anda), lalu restart komputer.
2. GPU perlu minimal generasi **NVIDIA GeForce GTX 900-series (Maxwell,
   2014) ke atas** — hampir semua GPU NVIDIA yang dijual 5 tahun terakhir
   sudah memenuhi ini.
3. Sebaiknya update driver ke versi terbaru (lewat NVIDIA App / GeForce
   Experience, atau unduh manual) supaya kompatibel dengan CUDA versi
   terbaru.

---

## Metode 1 (DIREKOMENDASIKAN) — Install via pip, Tanpa Akun NVIDIA

Ini cara paling ringkas: dua library yang MaxSubtitle butuhkan (cuBLAS,
cuDNN) diinstall langsung sebagai paket Python biasa lewat pip — **tidak
perlu** mengunduh installer 3GB dari NVIDIA, **tidak perlu** bikin akun
developer NVIDIA (yang biasanya diminta untuk unduh cuDNN manual).

> Saya sudah update MaxSubtitle supaya begitu paket ini terpasang,
> aplikasi otomatis menemukan lokasinya sendiri — **Anda tidak perlu
> mengedit PATH Windows secara manual**. Kalau Anda pakai ZIP MaxSubtitle
> yang saya kirim sebelumnya, update dulu source code-nya (lihat catatan
> di akhir tutorial ini).

### Langkah-langkah

1. Buka Command Prompt, masuk ke folder MaxSubtitle, aktifkan venv:
   ```bat
   cd C:\path\ke\folder\MaxSubtitle
   venv\Scripts\activate
   ```
2. Install dua paket ini (total unduhan sekitar 1.2 GB, tergantung
   kecepatan internet bisa beberapa menit):
   ```bat
   pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
   ```
3. Selesai. Tidak ada langkah tambahan.

### Verifikasi

Jalankan script diagnostik yang sudah saya siapkan (`cek_gpu.py`, ada di
folder MaxSubtitle):

```bat
python cek_gpu.py
```

Script ini mengecek 4 hal berurutan: driver NVIDIA → deteksi GPU oleh
ctranslate2 → tes inferensi ringan sungguhan (memastikan cuBLAS/cuDNN
benar-benar bisa dimuat, bukan cuma "device terdeteksi") → ringkasan.
Kalau semua lolos, GPU Anda siap dipakai — buka MaxSubtitle seperti
biasa, GPU akan otomatis dipakai tanpa perlu diatur apa pun (device di
Pengaturan tetap "Otomatis").

### Kalau mau build ulang exe dengan GPU ikut terbundle

Supaya `MaxSubtitle.exe` hasil build punya dukungan GPU **tanpa orang
lain yang pakai exe Anda perlu install apa pun**, tambahkan ke
`requirements.txt` (hapus tanda `#` di dua baris paling bawah), lalu
`pip install -r requirements.txt` dan build ulang seperti biasa. Ini
akan menambah ukuran installer sekitar 1.2 GB — pertimbangkan ini kalau
mau bagikan exe-nya ke orang lain yang mungkin tidak semua punya GPU
NVIDIA.

---

## Metode 2 — Install CUDA Toolkit Lengkap dari NVIDIA (Cara Resmi/Tradisional)

Pakai cara ini kalau Anda juga butuh CUDA Toolkit untuk keperluan lain
(bukan cuma MaxSubtitle), misalnya development CUDA/deep learning secara
umum.

### 2.1 Install CUDA Toolkit

1. Buka https://developer.nvidia.com/cuda-downloads
2. Pilih: **Windows** > versi Windows Anda > **exe (local)**
3. Unduh (sekitar 3 GB) dan jalankan installer, pilih **Express
   Installation**
4. Restart komputer setelah selesai

### 2.2 Install cuDNN

Ini bagian yang sering bikin bingung karena butuh akun NVIDIA gratis:

1. Buka https://developer.nvidia.com/cudnn
2. Klik **Download cuDNN**, login/daftar akun NVIDIA Developer (gratis)
   kalau diminta
3. Pilih versi **cuDNN 9.x** yang sesuai dengan CUDA 12 yang tadi
   diinstall, pilih installer untuk **Windows**
4. Setelah terunduh (biasanya berupa file .zip), extract, lalu **copy**
   isi foldernya ke folder instalasi CUDA Toolkit tadi:
   - `bin\*` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin`
   - `include\*` → `...\CUDA\v12.x\include`
   - `lib\*` → `...\CUDA\v12.x\lib`

### 2.3 Pastikan masuk PATH

Installer CUDA Toolkit biasanya otomatis menambahkan dirinya ke PATH
Windows. Untuk memastikan:

1. Tekan tombol Windows, ketik "environment variables", buka **"Edit the
   system environment variables"**
2. Klik **Environment Variables**, cari **Path** di bagian System
   variables, klik **Edit**
3. Pastikan ada baris seperti
   `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin`
4. Kalau belum ada, klik **New** dan tambahkan manual
5. **Restart Command Prompt** (atau restart komputer) supaya PATH baru
   terbaca

### Verifikasi

Sama seperti Metode 1, jalankan:
```bat
python cek_gpu.py
```

---

## Troubleshooting

**`cek_gpu.py` berhenti di langkah [1/4] — nvidia-smi tidak ditemukan**
Driver NVIDIA belum terpasang atau belum masuk PATH. Install/reinstall
driver dari nvidia.com, lalu restart komputer.

**Lolos [1/4] dan [2/4], tapi gagal di [3/4] (tes inferensi)**
Ini persis kondisi yang menyebabkan error Anda sebelumnya — device
terdeteksi tapi library-nya belum benar-benar bisa dimuat. Pastikan
Anda sudah menjalankan salah satu Metode 1 atau 2 di atas dengan
lengkap, lalu jalankan ulang `cek_gpu.py`. Kalau masih gagal, baca
pesan error persisnya — biasanya menyebutkan versi/nama file yang
bermasalah.

**Sudah install tapi MaxSubtitle masih pakai CPU**
Pastikan file `app/core/transcriber.py` Anda sudah versi terbaru (yang
punya fungsi `_register_nvidia_pip_dll_dirs`) — cek dengan membuka file
itu dan cari kata "add_dll_directory". Kalau belum ada, ganti dengan
source code dari ZIP MaxSubtitle terbaru yang saya kirim.

**pip install nvidia-cublas-cu12 gagal / sangat lambat**
Paket ini besar (~550MB). Kalau koneksi tidak stabil, coba lagi —
pip otomatis melanjutkan dari file yang sudah terunduh sebagian pada
beberapa kasus, atau gunakan `pip install --timeout 120 ...` untuk
kasih waktu lebih.

**Ingin uninstall / bersihkan lagi**
```bat
pip uninstall nvidia-cublas-cu12 nvidia-cudnn-cu12
```
Aplikasi otomatis kembali memakai CPU, tidak ada langkah tambahan yang
perlu diubah.

---

## Ringkasan: Metode 1 vs Metode 2

| | Metode 1 (pip) | Metode 2 (CUDA Toolkit resmi) |
|---|---|---|
| Ukuran unduhan | ~1.2 GB | ~3 GB + cuDNN terpisah |
| Perlu akun NVIDIA | Tidak | Ya (untuk cuDNN) |
| Edit PATH manual | Tidak (sudah otomatis) | Ya |
| Berguna untuk aplikasi lain juga | Tidak (khusus venv MaxSubtitle) | Ya (CUDA Toolkit system-wide) |
| Direkomendasikan untuk | Hampir semua orang | Yang juga butuh CUDA untuk keperluan lain |

---

*Bagian dari project MaxSubtitle — Copyright (c) iman.mn_*
