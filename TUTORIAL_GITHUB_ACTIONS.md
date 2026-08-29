# Tutorial Lengkap: Build MaxSubtitle Otomatis via GitHub Actions (Cloud)

Panduan ini untuk mengubah source code MaxSubtitle jadi file `.exe` dan
installer Windows **tanpa perlu komputer Windows sama sekali** dan **tanpa
install Python/PyInstaller/Inno Setup secara lokal**. Semua proses build
betulan terjadi di komputer Windows milik GitHub di cloud — hasilnya adalah
exe Windows asli, bukan hasil cross-compile.

---

## Yang Anda Butuhkan

- [ ] Akun GitHub (gratis) — daftar di https://github.com/signup kalau
      belum punya
- [ ] File `MaxSubtitle_v2_source.zip` yang sudah saya buatkan sebelumnya,
      sudah di-extract di komputer Anda
- [ ] Browser web (Chrome/Firefox/Edge, apa saja)
- [ ] Waktu sekitar 20-30 menit (sebagian besar cuma menunggu proses build)

Tidak perlu install apa pun lagi selain browser untuk metode dasar di
tutorial ini.

---

## Bagian 1 — Buat Repository di GitHub

### 1.1 Login ke GitHub

Buka https://github.com dan login. Kalau belum punya akun, klik **Sign up**
dan ikuti langkahnya (email, password, username, verifikasi).

### 1.2 Buat repository baru

1. Setelah login, klik ikon **"+"** di pojok kanan atas, lalu pilih
   **"New repository"**. (Atau langsung buka https://github.com/new)
2. Isi form:
   - **Repository name**: bebas, misalnya `maxsubtitle`
   - **Description**: boleh dikosongkan
   - Pilih **Public** atau **Private** — baca dulu penjelasan di bawah
     sebelum memutuskan
   - **JANGAN** centang "Add a README file", "Add .gitignore", atau
     "Choose a license" — biarkan semua kosong, karena project kita sudah
     punya file-file ini sendiri
3. Klik tombol hijau **"Create repository"**

#### Public vs Private — mana yang dipilih?

Ini penting karena memengaruhi kuota gratis Anda. Saya sudah cek data
kuota GitHub Actions terbaru (Agustus 2026):

| | **Public** | **Private** |
|---|---|---|
| Menit build gratis | **Tidak terbatas** | 2.000 menit/bulan (setara Linux) |
| Runner Windows | Gratis, tidak terbatas | Dihitung **2x** dari menit aslinya terhadap kuota |
| Storage hasil build (artifact) | **Tidak terbatas** | 500 MB (dipakai bersama-sama cache) |
| Siapa bisa lihat kode | Semua orang | Cuma Anda (+ orang yang diundang) |

**Rekomendasi saya: pakai Public**, kecuali Anda punya alasan khusus
kode harus rahasia. Alasannya konkret: hasil build MaxSubtitle
(exe + semua library AI seperti faster-whisper, ctranslate2, OpenCV)
ukurannya besar — ratusan MB. Di repo Private, ini bisa cepat memenuhi
kuota 500 MB gratis (bahkan mungkin dari satu kali build saja), sedangkan
di repo Public sama sekali tidak ada batasan ukuran atau jumlah build.

Kalau tetap mau Private, tidak masalah — cuma nanti di bagian
Troubleshooting ada tips mengatur retensi artifact supaya kuota tidak
cepat penuh.

---

## Bagian 2 — Upload Project ke Repository

Ada dua cara. Pilih **Metode A** kalau tidak familiar command line, atau
**Metode B** kalau sudah biasa pakai Git (lebih cepat untuk update
berikutnya).

### Metode A — Upload via Browser (tanpa command line)

1. Setelah repository dibuat, Anda akan melihat halaman "Quick setup"
   dengan beberapa opsi. Cari dan klik link **"uploading an existing
   file"**.
2. Buka File Explorer di komputer Anda, masuk ke **dalam** folder
   `MaxSubtitle` hasil extract ZIP (jadi Anda melihat isi-nya: folder
   `app`, `assets`, `tests`, `.github`, file `main.py`,
   `requirements.txt`, dll — bukan folder `MaxSubtitle`-nya sendiri).
3. Pilih **semua isi** folder tersebut (Ctrl+A), lalu **drag-and-drop**
   ke area upload di halaman GitHub tadi. GitHub akan mempertahankan
   struktur folder secara otomatis, termasuk folder `.github` yang
   berisi workflow build.
4. Tunggu sampai semua file selesai ter-upload (ada progress bar per
   file).
5. Scroll ke bawah, di bagian **"Commit changes"** biarkan pesan
   default atau tulis sendiri (misal "Upload MaxSubtitle v2.0"), lalu
   klik tombol hijau **"Commit changes"**.
6. Anda akan kembali ke halaman utama repo. **Cek folder `.github` ada
   di daftar file** — ini penting karena berisi workflow build. Kalau
   tidak ada, ulangi upload dan pastikan folder itu ikut ter-drag.

> **Perhatian umum**: kalau saat extract ZIP Anda mendapat folder
> bertingkat dua (`MaxSubtitle/MaxSubtitle/app/...`), yang di-drag ke
> GitHub adalah isi folder yang PALING DALAM (yang langsung berisi
> `app`, `main.py`, dst), bukan folder pembungkusnya.

### Metode B — Via Git Command Line

Kalau belum punya Git, install dulu dari https://git-scm.com/download/win

Buka Command Prompt atau PowerShell, arahkan ke folder MaxSubtitle:

```bat
cd C:\path\ke\folder\MaxSubtitle
git init
git add .
git commit -m "Upload MaxSubtitle v2.0"
git branch -M main
git remote add origin https://github.com/USERNAME/maxsubtitle.git
git push -u origin main
```

Ganti `USERNAME` dengan username GitHub Anda dan `maxsubtitle` dengan
nama repo yang tadi dibuat. Saat `git push`, browser biasanya otomatis
terbuka minta login/otorisasi GitHub — ikuti saja.

---

## Bagian 3 — Jalankan Workflow Build

1. Di halaman repository, klik tab **"Actions"** (ada di baris menu atas,
   sejajar dengan "Code", "Issues", "Pull requests").
2. Di sidebar kiri, klik workflow bernama
   **"Build MaxSubtitle Windows Installer"**.
3. Di kanan atas daftar run, klik tombol **"Run workflow"** (biasanya
   berwarna abu-abu/biru dengan ikon dropdown).
4. Muncul kotak kecil dengan pilihan branch (biarkan default: `main`),
   lalu klik tombol hijau **"Run workflow"** di dalam kotak itu.
5. Tunggu beberapa detik, refresh halaman — akan muncul satu baris run
   baru dengan titik kuning berputar (tanda sedang berjalan).

### Memantau progres

Klik run yang sedang berjalan itu untuk masuk ke halaman detail. Anda
akan melihat diagram job **"build-windows"** dengan langkah-langkah
berikut, berjalan berurutan:

1. Checkout kode
2. Setup Python
3. Install dependency Python
4. Jalankan self-test
5. Build exe dengan PyInstaller
6. Install Inno Setup
7. Build installer Windows
8. Upload MaxSubtitle.exe (folder aplikasi)
9. Upload installer

Klik tiap langkah untuk melihat log detail-nya secara real-time. Total
waktu biasanya **sekitar 10-15 menit** (langkah "Build exe dengan
PyInstaller" yang paling lama, karena mengunduh & mem-bundling
library AI seperti faster-whisper dan OpenCV).

Tanda run selesai: titik kuning berubah jadi **centang hijau** (sukses)
atau **silang merah** (gagal — lihat bagian Troubleshooting).

---

## Bagian 4 — Unduh Hasil Build

Setelah run selesai dengan centang hijau:

1. Masih di halaman run yang sama, **scroll ke paling bawah**.
2. Ada bagian **"Artifacts"** dengan dua item:
   - **MaxSubtitle-app-portable** — folder aplikasi lengkap, siap pakai
     tanpa install (portable)
   - **MaxSubtitle-Setup-installer** — installer wizard siap pakai
3. Klik masing-masing untuk mengunduh (otomatis dalam bentuk `.zip`).
4. Extract hasil unduhan di komputer Windows Anda.

### Memakai hasilnya

- **Kalau unduh installer**: extract, lalu jalankan
  `MaxSubtitle_Setup.exe` di dalamnya. Ikuti wizard instalasi seperti
  install aplikasi Windows pada umumnya (pilih lokasi install, buat
  shortcut Desktop kalau mau, dll).
- **Kalau unduh versi portable**: extract, lalu langsung jalankan
  `MaxSubtitle.exe` di dalam folder hasil extract — tidak perlu proses
  instalasi, bisa langsung dipakai atau dipindah ke komputer Windows
  lain.

> **Catatan**: MaxSubtitle butuh ffmpeg untuk membaca video/audio.
> Kalau belum ada ffmpeg di komputer target, ikuti panduan di README
> bagian Prasyarat (unduh ffmpeg, taruh di folder `ffmpeg\` di sebelah
> `MaxSubtitle.exe`, atau tambahkan ke PATH Windows).

> Artifact ini tersimpan di GitHub selama **90 hari** sejak dibuat,
> setelah itu otomatis terhapus (bukan berarti aplikasinya hilang — file
> yang sudah Anda unduh ke komputer tetap aman selamanya, ini cuma soal
> penyimpanan sementara di sisi GitHub).

---

## Bagian 5 (Bonus) — Auto-Build Lewat Tag Versi

Selain klik manual "Run workflow", workflow ini juga otomatis jalan
setiap kali Anda push **tag versi** — berguna kalau nanti mau rilis
versi baru secara rapi:

```bat
git tag v2.0.0
git push --tags
```

Ini otomatis memicu build baru tanpa perlu buka GitHub sama sekali.

---

## Bagian 6 — Update Project di Kemudian Hari

Kalau nanti Anda mengubah kode MaxSubtitle (misal minta saya tambah
fitur baru) dan mau build ulang:

- **Metode A (browser)**: buka repo di GitHub, masuk ke folder yang
  filenya berubah, klik file itu, klik ikon pensil (Edit), atau upload
  ulang file yang berubah lewat "Add file" > "Upload files".
- **Metode B (Git)**: di folder project, jalankan:
  ```bat
  git add .
  git commit -m "Update fitur X"
  git push
  ```

Lalu ulangi Bagian 3 (buka tab Actions, klik "Run workflow" lagi).

---

## Troubleshooting

**Workflow tidak muncul di tab Actions**
Pastikan folder `.github/workflows/build-windows.yml` benar-benar
ter-upload di posisi yang tepat (bukan tertimbun folder ekstra karena
salah extract ZIP). Cek langsung dengan membuka folder `.github` di
halaman repo GitHub Anda.

**Tombol "Run workflow" tidak kelihatan**
Pastikan Anda mengklik nama workflow-nya dulu di sidebar kiri (bukan
cuma buka tab Actions saja), dan pastikan Anda punya akses write ke
repo tersebut (kalau ini repo sendiri, otomatis punya).

**Run gagal (silang merah) di langkah "Install dependency Python"**
Biasanya masalah jaringan sementara di server GitHub — klik tombol
**"Re-run jobs"** di halaman run tersebut, biasanya langsung berhasil
di percobaan kedua.

**Run gagal di langkah "Jalankan self-test"**
Ini menandakan ada masalah nyata di kode, bukan masalah build. Klik
langkah itu untuk baca pesan error lengkapnya — kirimkan pesan errornya
ke saya kalau butuh bantuan diagnosis.

**Run gagal di langkah "Build installer Windows"**
Biasanya karena `installer.iss` mereferensikan file yang belum ada
(jarang terjadi kalau langkah sebelumnya sukses semua). Cek log detail
di langkah tersebut.

**Bagian "Artifacts" kosong / tidak ada**
Berarti build gagal sebelum sampai ke langkah upload — cek langkah mana
yang merah di log, atau artifact sudah lewat 90 hari dan otomatis
terhapus (build ulang saja).

**Repo Private, muncul pesan kuota storage penuh**
Buka **Settings** repo > **Actions** > **General**, scroll ke
**"Artifact and log retention"**, turunkan dari default 90 hari jadi
misalnya 7 hari — ini bikin artifact lama otomatis kehapus lebih cepat
jadi kuota tidak numpuk. Atau, cara paling simpel: ubah repo jadi
**Public** lewat Settings > scroll ke bawah > "Danger Zone" > "Change
visibility" (kalau kode tidak masalah dilihat publik).

---

*Tutorial ini bagian dari project MaxSubtitle — Copyright (c) iman.mn_*
