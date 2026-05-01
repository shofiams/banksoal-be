import os
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import DeadlineExceeded, ResourceExhausted, ServiceUnavailable

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

# ─────────────────────────────────────────────
# Konstanta — ubah di sini kalau perlu tuning
# ─────────────────────────────────────────────
REQUEST_TIMEOUT   = 120  # detik maksimal per satu LLM call
MAX_RETRIES       = 3    # berapa kali coba ulang kalau gagal
RETRY_DELAY_BASE  = 5    # detik jeda awal (dikalikan nomor attempt)
MAX_SOAL_PER_CALL = 8    # batas soal per satu LLM call (chunked generation)

# proses generate soal
def generate_text(prompt: str, timeout: int = REQUEST_TIMEOUT) -> str:
    """
    Kirim prompt ke Gemini dengan:
    - Timeout eksplisit (tidak gantung selamanya)
    - Retry otomatis 3x saat timeout / server down / rate limit

    Raises exception terakhir kalau semua retry habis.
    """
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[Gemini] Attempt {attempt}/{MAX_RETRIES} | prompt: {len(prompt)} chars")
            response = model.generate_content(
                prompt,
                request_options={"timeout": timeout}
            )
            logger.info(f"[Gemini] Berhasil pada attempt {attempt}")
            return response.text

        except (DeadlineExceeded, ServiceUnavailable) as e:
            last_exc = e
            wait = RETRY_DELAY_BASE * attempt
            logger.warning(f"[Gemini] Timeout/Unavailable (attempt {attempt}). Retry dalam {wait}s. Error: {e}")
            time.sleep(wait)

        except ResourceExhausted as e:
            # Rate limit — tunggu lebih lama
            last_exc = e
            wait = RETRY_DELAY_BASE * attempt * 2
            logger.warning(f"[Gemini] Rate limit (attempt {attempt}). Retry dalam {wait}s. Error: {e}")
            time.sleep(wait)

        except Exception as e:
            # Error lain (misal: invalid API key, model error) — langsung raise
            logger.error(f"[Gemini] Error tidak terduga: {e}")
            raise

    logger.error(f"[Gemini] Semua {MAX_RETRIES} attempt gagal.")
    raise last_exc


def generate_text_chunked(
    build_prompt_fn,
    total_soal: int,
    chunk_size: int = MAX_SOAL_PER_CALL,
    **prompt_kwargs
) -> list:
    """
    Generate soal dalam batch kecil supaya tidak timeout.

    Cara kerja:
    - Kalau total_soal=10 dan chunk_size=5 → 2 LLM call masing-masing 5 soal
    - Setiap batch menggunakan generate_text() yang sudah punya retry

    Parameter:
    - build_prompt_fn : fungsi builder prompt, WAJIB menerima kwarg 'jumlah_soal'
    - total_soal      : total soal yang ingin dihasilkan
    - chunk_size      : maksimum soal per satu LLM call
    - **prompt_kwargs : argumen lain yang diteruskan ke build_prompt_fn
    """
    from app.services.llm.utils.json_parser import clean_and_parse_json

    all_results = []
    remaining   = total_soal

    while remaining > 0:
        batch = min(remaining, chunk_size)
        logger.info(f"[Chunked] Batch: {batch} soal | sisa: {remaining}")

        prompt = build_prompt_fn(jumlah_soal=batch, **prompt_kwargs)
        raw    = generate_text(prompt)
        parsed = clean_and_parse_json(raw)

        if isinstance(parsed, list) and len(parsed) > 0:
            all_results.extend(parsed)
            remaining -= len(parsed)
            if len(parsed) < batch:
                # LLM menghasilkan lebih sedikit dari yang diminta, hentikan loop
                logger.warning(f"[Chunked] LLM return {len(parsed)}/{batch}. Loop dihentikan.")
                break
        else:
            logger.warning("[Chunked] Gagal parse JSON. Batch ini dilewati.")
            break

        # Jeda kecil antar batch agar tidak kena rate limit
        if remaining > 0:
            time.sleep(2)

    logger.info(f"[Chunked] Selesai. Total soal terkumpul: {len(all_results)}")
    return all_results