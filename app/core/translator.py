"""Auto-translate teks subtitle memakai Google Translate (via deep-translator).

Diberi mekanisme retry + delay antar-batch karena endpoint gratis Google
Translate kadang membatasi laju permintaan (rate limit)."""
import time
from typing import Callable, List, Optional

ProgressCB = Optional[Callable[[float, str], None]]


class TranslateCancelled(Exception):
    pass


class Translator:
    def __init__(self, source: str = "auto", target: str = "id"):
        self.source = source
        self.target = target
        self.cancel_requested = False

    def translate_batch(self, texts: List[str], progress_callback: ProgressCB = None,
                         batch_size: int = 15) -> List[str]:
        self.cancel_requested = False
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source=self.source, target=self.target)
        results: List[str] = []
        total = len(texts)
        if total == 0:
            return results

        for i in range(0, total, batch_size):
            if self.cancel_requested:
                raise TranslateCancelled()
            batch = texts[i:i + batch_size]
            translated = self._translate_batch_with_retry(translator, batch)
            results.extend(translated)
            if progress_callback:
                done = min(total, i + len(batch))
                progress_callback(done / total * 100, f"Menerjemahkan... {done}/{total} baris")
            time.sleep(0.15)  # jeda kecil, jaga-jaga rate limit
        return results

    def _translate_batch_with_retry(self, translator, batch: List[str], retries: int = 3) -> List[str]:
        non_empty_idx = [i for i, t in enumerate(batch) if t and t.strip()]
        if not non_empty_idx:
            return list(batch)

        for attempt in range(retries):
            try:
                to_translate = [batch[i] for i in non_empty_idx]
                translated = translator.translate_batch(to_translate)
                out = list(batch)
                for idx, t in zip(non_empty_idx, translated):
                    out[idx] = t if t else batch[idx]
                return out
            except Exception:
                if attempt == retries - 1:
                    return self._translate_one_by_one(translator, batch)
                time.sleep(0.8 * (attempt + 1))
        return list(batch)

    def _translate_one_by_one(self, translator, batch: List[str]) -> List[str]:
        out = []
        for text in batch:
            if not text or not text.strip():
                out.append(text)
                continue
            try:
                out.append(translator.translate(text))
            except Exception:
                out.append(text)  # fallback: biarkan teks asli kalau gagal total
        return out

    def cancel(self):
        self.cancel_requested = True


SUPPORTS_AUTO_DETECT = True
