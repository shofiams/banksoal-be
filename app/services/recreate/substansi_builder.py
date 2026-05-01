import re

# Kata-kata umum yang tidak representatif sebagai konsep
STOPWORDS = {
    "yang", "adalah", "dari", "pada", "dan", "atau", "ini", "itu",
    "di", "ke", "oleh", "dengan", "untuk", "dalam", "tidak", "dapat",
    "akan", "telah", "juga", "sebagai", "tersebut", "secara", "suatu",
    "sebuah", "antara", "apa", "mengapa", "bagaimana", "manakah",
    "berikut", "pernyataan", "benar", "salah", "pilih", "tentang",
    "disebut", "merupakan", "terjadi", "proses", "fungsi", "peran",
}

# tahap ke 7 recreate
# tahap utama substansi
def build_substansi(retrieved_results):
    """
    Membangun substansi berdasarkan hasil retrieval FAISS.
    Substansi berisi:
    - Konsep utama
    - Pola pertanyaan
    - Struktur jawaban
    - Level kognitif dominan
    """

    if not retrieved_results:
        raise ValueError("Tidak ada soal referensi untuk membangun substansi.")

    konsep_set = set()
    pola_list = []
    level_list = []

    for item in retrieved_results:
        # ← FIX: gunakan key yang benar sesuai struktur FaissIndex
        text = item.get("text_original", item.get("text_normalized", item.get("text", "")))
        level = item.get("level", "")

        konsep_dari_teks = extract_concept(text)
        konsep_set.update(konsep_dari_teks)   # update set agar unik lintas soal
        pola_list.append(detect_question_type(text))
        level_list.append(level)

    substansi = {
        "konsep_utama": sorted(konsep_set)[:6],         # maks 6 konsep paling relevan
        "pola_pertanyaan": list(set(pola_list)),
        "struktur_jawaban": "1 jawaban benar + 4 pengecoh",
        "level_referensi": max(set(level_list), key=level_list.count)
    }

    return substansi

# tahap 8 recreate_prompt_builder


def extract_concept(text: str) -> list:
    """
    Ekstrak kata-kata kunci bermakna dari teks soal sebagai konsep utama.
    Mengembalikan list kata kunci (bukan string tunggal).
    """
    if not text:
        return []

    # Ambil bagian pertanyaan saja (sebelum "?" atau sebelum "opsi:")
    text = text.split("?")[0]
    text = text.split("opsi:")[0]

    # Bersihkan: lowercase, hapus nomor, hapus tanda baca
    text = text.lower()
    text = re.sub(r"\d+[\.\)]\s*", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Ambil kata dengan panjang >= 4 huruf yang bukan stopword
    kata_list = [
        kata for kata in text.split()
        if len(kata) >= 4 and kata not in STOPWORDS
    ]

    # Kembalikan maks 3 kata kunci per soal
    return kata_list[:3]


def detect_question_type(text: str) -> str:
    """
    Deteksi pola pertanyaan dari teks soal.
    Mendukung teks yang diawali nomor (mis. "1. Mengapa...").
    """
    if not text:
        return "pertanyaan umum"

    # Bersihkan nomor di awal ("1. ", "2) ", dst) sebelum deteksi
    text_clean = re.sub(r"^\d+[\.\)]\s*", "", text.lower().strip())

    if text_clean.startswith("apa"):
        return "pertanyaan konsep langsung"
    elif text_clean.startswith("mengapa") or text_clean.startswith("kenapa"):
        return "pertanyaan sebab-akibat"
    elif text_clean.startswith("bagaimana"):
        return "pertanyaan proses"
    elif text_clean.startswith("sebutkan") or text_clean.startswith("jelaskan"):
        return "pertanyaan deskriptif"
    elif text_clean.startswith("manakah") or text_clean.startswith("yang mana"):
        return "pertanyaan identifikasi"
    elif text_clean.startswith("berapa"):
        return "pertanyaan kuantitatif"
    else:
        return "pertanyaan umum"