"""Auto-translate teks subtitle memakai Google Translate (via deep-translator),
dengan fallback otomatis ke mesin cadangan (MyMemory) kalau Google sedang
diblokir/limit.

## Kenapa dulu kolom "Terjemahan" bisa penuh teks "Error 500 (Server Error)..."

Endpoint gratis Google Translate yang dipakai deep-translator kadang TIDAK
mengembalikan HTTP error saat sedang membatasi/blokir permintaan. Ia
membalas HTTP 200 (dianggap "sukses" oleh library) tapi isi halamannya
adalah halaman error generik Google ("Error 500 (Server Error)!!1500.
That's an error. There was an error. Please try again later. That's all
we know."). Karena status HTTP-nya 200, deep-translator tidak melempar
exception - ia parsing halaman itu, menemukan sebuah <div> yang cocok
dengan selector cadangannya, lalu isinya (teks error tsb) dikembalikan
APA ADANYA seolah-olah itu hasil terjemahan sungguhan. Itulah yang muncul
identik di semua baris pada laporan bug: bukan bug per-bahasa, tapi
seluruh proses terjemahan sedang "gagal secara diam-diam".

MyMemory (dipakai sbg cadangan) punya masalah serupa dgn caranya sendiri:
kalau kuota gratis harian habis, ia membalas HTTP 200 + JSON valid, tapi
field "translatedText"-nya cuma berisi pesan peringatan kuota - bukan
error, tapi bukan terjemahan juga.

## Cara modul ini menanganinya
1. Setiap hasil dari mesin terjemahan divalidasi (`_looks_like_failed_response`)
   sebelum dianggap sukses. Kalau polanya cocok dgn halaman
   error/pesan-kuota yang diketahui, itu diperlakukan sbg KEGAGALAN (retry),
   bukan hasil valid - supaya tidak pernah lagi tampil sbg "terjemahan".
2. Tiap baris diterjemahkan (dan divalidasi) satu-per-satu dengan retry +
   jeda kecil antar-request, bukan per-batch - jadi satu baris yang gagal
   tidak membuang hasil baris lain yang sudah berhasil, dan burst request
   yang gampang memicu limit Google bisa dikurangi.
3. Kalau satu mesin gagal berkali-kali berturut-turut (kemungkinan sedang
   down total / tidak ada internet), mesin itu "dimatikan sementara" utk
   sisa proses ini dan otomatis lanjut ke mesin cadangan - supaya prosesnya
   tidak lambat menunggu timeout berulang untuk tiap baris.
4. Baris yang tetap gagal di SEMUA mesin akan mempertahankan teks ASLI
   (bukan pernah menampilkan halaman error) dan dihitung di `failed_count`
   supaya UI bisa memberi tahu pengguna berapa baris yang perlu
   diterjemahkan ulang/manual.
5. Setiap baris tetap dikirim dgn source="auto" secara independen (bukan
   sekali utk seluruh video) - jadi video yang barisnya campur beberapa
   bahasa tetap diterjemahkan dengan benar per baris, selama request-nya
   sendiri berhasil (lihat poin 1-3 di atas).
6. Opsional: LibreTranslate lokal. Kalau `use_libretranslate=True`, mesin
   ini dicoba PALING PERTAMA (sebelum Google) karena jalan di komputer
   sendiri lewat server yang dijalankan pengguna sendiri - artinya BENAR2
   tanpa limit harian & gratis selamanya, tidak pernah menghubungi Google/
   MyMemory sama sekali selama server lokalnya menyala. Kalau server itu
   belum/tidak menyala, requestnya gagal cepat (connection error) dan
   otomatis lanjut ke Google -> MyMemory spt biasa, jadi tidak pernah bikin
   aplikasi berhenti total hanya karena lupa menyalakan LibreTranslate.
   Catatan: deep-translator mewajibkan parameter api_key diisi walau server
   lokal defaultnya TIDAK butuh autentikasi - dalam kasus itu modul ini
   mengisi nilai placeholder saja (server lokal tanpa --api-keys akan
   mengabaikan parameter yang tidak ia kenali).

Selain itu, ada perbaikan kecil: aplikasi ini punya opsi bahasa target
"Mandarin" berkode "zh", tapi Google Translate hanya mengenal "zh-CN"
(simplified) / "zh-TW" (traditional) - kode "zh" polos akan langsung
ditolak (LanguageNotSupportedException) sebelum sempat mengirim satu pun
request. `_normalize_lang_code` menormalkan kode semacam ini."""
import time
from typing import Callable, List, Optional, Tuple

ProgressCB = Optional[Callable[[float, str], None]]


class TranslateCancelled(Exception):
    pass


class TranslationEngineError(Exception):
    """Dipakai internal saat mesin terjemahan mengembalikan hasil yang tidak
    valid (halaman error, pesan kuota, atau kosong) walau tanpa exception
    HTTP - lihat docstring modul ini."""
    pass


# Potongan teks (huruf kecil semua) yang KHAS muncul saat mesin terjemahan
# gagal secara diam-diam (HTTP 200 tapi isinya bukan terjemahan sungguhan).
# Kalau salah satu pola ini ditemukan di "hasil terjemahan", hasil tsb
# dianggap GAGAL, bukan diterima sbg terjemahan yang valid.
_FAILURE_MARKERS = [
    # Halaman error generik Google Translate saat diblokir/rate-limit
    "error 500 (server error)",
    "that's an error",
    "that's all we know",
    "there was an error. please try again later",
    # Pesan kuota MyMemory ketika limit gratis harian habis
    "mymemory warning",
    "you used all available free translations",
]

# Kode bahasa yang dipakai UI aplikasi ini tapi tidak persis sama dengan
# yang diharapkan Google Translate.
_LANG_CODE_OVERRIDES = {
    "zh": "zh-CN",  # aplikasi cuma punya 1 opsi "Mandarin" -> pakai simplified
}


def _looks_like_failed_response(text: Optional[str]) -> bool:
    """True kalau `text` sebenarnya pesan error/kuota yang ketlisut, bukan
    hasil terjemahan sungguhan."""
    if not text:
        return False
    low = text.lower().replace("\u2019", "'")  # normalisasi kutip miring
    return any(marker in low for marker in _FAILURE_MARKERS)


def _normalize_lang_code(code: str) -> str:
    if not code:
        return code
    return _LANG_CODE_OVERRIDES.get(code, code)


def _lang_name_for(code: str) -> Optional[str]:
    """Cari nama bahasa lengkap (mis. 'indonesian') dari kode singkat gaya
    Google (mis. 'id'). MyMemoryTranslator memakai skema kode sendiri yang
    beda (mis. 'id-ID' bukan 'id'), tapi ia juga menerima nama bahasa
    lengkap dan memetakannya sendiri secara internal - jadi mencari nama
    yang tepat di sini lebih aman daripada menebak kode MyMemory secara
    manual utk tiap bahasa."""
    if code == "auto":
        return "auto"
    from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES

    google_code = _normalize_lang_code(code)
    for name, mapped_code in GOOGLE_LANGUAGES_TO_CODES.items():
        if mapped_code == google_code:
            return name
    return None


class Translator:
    def __init__(self, source: str = "auto", target: str = "id",
                 use_libretranslate: bool = False,
                 libretranslate_url: str = "http://localhost:5000/",
                 libretranslate_api_key: str = ""):
        self.source = source
        self.target = target
        self.use_libretranslate = use_libretranslate
        self.libretranslate_url = libretranslate_url
        self.libretranslate_api_key = libretranslate_api_key
        self.cancel_requested = False
        # Jumlah baris yang akhirnya gagal diterjemahkan di SEMUA mesin pada
        # pemanggilan translate_batch() terakhir (teks asli dipertahankan
        # utk baris itu). UI bisa memakai ini utk memberi peringatan.
        self.failed_count = 0

    def _build_engines(self) -> List[Tuple[str, object]]:
        """Siapkan daftar mesin terjemahan yang dicoba berurutan.

        Kalau LibreTranslate lokal diaktifkan, ia dicoba PALING PERTAMA
        (tanpa limit, gratis selamanya, jalan di komputer sendiri). Google
        dicoba berikutnya (kualitas biasanya terbaik utk kalimat), lalu
        MyMemory sbg cadangan terakhir kalau keduanya gagal."""
        engines: List[Tuple[str, object]] = []

        if self.use_libretranslate:
            try:
                from deep_translator import LibreTranslator
                from deep_translator.constants import LIBRE_LANGUAGES_TO_CODES

                src_ok = self.source == "auto" or self.source in LIBRE_LANGUAGES_TO_CODES.values()
                tgt_ok = self.target in LIBRE_LANGUAGES_TO_CODES.values()
                if src_ok and tgt_ok:
                    url = self.libretranslate_url or "http://localhost:5000/"
                    if not url.endswith("/"):
                        url += "/"
                    engines.append((
                        "LibreTranslate (lokal)",
                        LibreTranslator(
                            source=self.source,
                            target=self.target,
                            custom_url=url,
                            # deep-translator mewajibkan nilai ini terisi walau
                            # server lokal biasanya tidak butuh autentikasi -
                            # placeholder ini aman, akan diabaikan server yang
                            # tidak dijalankan dgn mode --api-keys.
                            api_key=self.libretranslate_api_key or "local-no-auth-needed",
                        ),
                    ))
                # kalau bahasa ini tidak didukung LibreTranslate (mis. Thai/
                # Melayu/Belanda blm ada di daftar deep-translator), lewati
                # saja mesin ini utk pasangan bahasa ini - lanjut ke Google.
            except Exception:
                pass  # server/paket tidak tersedia - lanjut ke mesin lain

        try:
            from deep_translator import GoogleTranslator
            engines.append((
                "Google Translate",
                GoogleTranslator(
                    source=_normalize_lang_code(self.source),
                    target=_normalize_lang_code(self.target),
                ),
            ))
        except Exception:
            pass  # kode bahasa tidak didukung Google - lewati mesin ini

        try:
            from deep_translator import MyMemoryTranslator
            from deep_translator.constants import MY_MEMORY_LANGUAGES_TO_CODES

            src_name = _lang_name_for(self.source)
            tgt_name = _lang_name_for(self.target)
            src_ok = src_name == "auto" or src_name in MY_MEMORY_LANGUAGES_TO_CODES
            tgt_ok = tgt_name in MY_MEMORY_LANGUAGES_TO_CODES  # target tak boleh "auto"
            if src_ok and tgt_ok:
                engines.append((
                    "MyMemory",
                    MyMemoryTranslator(source=src_name, target=tgt_name),
                ))
        except Exception:
            pass  # MyMemory tidak tersedia utk pasangan bahasa ini - lewati saja

        return engines

    def translate_batch(self, texts: List[str], progress_callback: ProgressCB = None,
                         batch_size: int = 15) -> List[str]:
        self.cancel_requested = False
        self.failed_count = 0
        results: List[str] = []
        total = len(texts)
        if total == 0:
            return results

        engines = self._build_engines()
        if not engines:
            raise RuntimeError(
                f"Tidak ada mesin terjemahan yang mendukung pasangan bahasa "
                f"'{self.source}' -> '{self.target}'. Coba pilih bahasa target lain."
            )

        consecutive_fail = {name: 0 for name, _ in engines}
        disabled: set = set()

        for i, text in enumerate(texts):
            if self.cancel_requested:
                raise TranslateCancelled()
            results.append(self._translate_one_line(engines, text, consecutive_fail, disabled))
            if progress_callback and ((i + 1) % batch_size == 0 or i + 1 == total):
                progress_callback((i + 1) / total * 100, f"Menerjemahkan... {i + 1}/{total} baris")

        return results

    def _translate_one_line(self, engines: List[Tuple[str, object]], text: str,
                             consecutive_fail: dict, disabled: set,
                             retries_per_engine: int = 2) -> str:
        if not text or not text.strip():
            return text

        for name, engine in engines:
            if name in disabled:
                continue
            for attempt in range(retries_per_engine):
                if self.cancel_requested:
                    raise TranslateCancelled()
                try:
                    result = engine.translate(text)
                except TranslateCancelled:
                    raise
                except Exception:
                    result = None
                time.sleep(0.1)  # jeda kecil tiap habis memanggil API - jaga rate limit

                if result and result.strip() and not _looks_like_failed_response(result):
                    consecutive_fail[name] = 0
                    return result

                if attempt < retries_per_engine - 1:
                    time.sleep(0.5 * (attempt + 1))  # backoff sebelum coba lagi

            consecutive_fail[name] += 1
            if consecutive_fail[name] >= 4:
                # Mesin ini kemungkinan sedang down total (diblokir / tidak ada
                # internet) - matikan sementara utk sisa proses ini supaya
                # tidak lambat menunggu timeout berulang tiap baris, dan
                # langsung lanjut ke mesin cadangan (kalau ada).
                disabled.add(name)

        # Semua mesin gagal utk baris ini - pertahankan teks ASLI. JANGAN
        # PERNAH mengembalikan halaman error/pesan kuota seolah-olah itu
        # terjemahan yang valid.
        self.failed_count += 1
        return text

    def cancel(self):
        self.cancel_requested = True


SUPPORTS_AUTO_DETECT = True
