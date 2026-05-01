def map_level_to_instruction(level: str) -> str:
    """
    Konversi level ke instruksi pencarian yang SPESIFIK.
    REVISI: support C1-C6 langsung, query lebih pendek & tajam
    agar IndoBERT tidak match ke metadata/noise.
    """
    level = level.upper()

    # Support sub-level C1-C6
    mapping_sub = {
        "C1": "definisi dan pengertian",
        "C2": "penjelasan dan deskripsi konsep",
        "C3": "mekanisme, proses, dan cara kerja",
        "C4": "analisis perbandingan dan hubungan sebab akibat",
        "C5": "evaluasi dan penilaian konsep",
        "C6": "penerapan konsep dalam konteks baru",
    }

    mapping_legacy = {
        "LOTS": "definisi, pengertian, dan penjelasan konsep dasar",
        "MOTS": "mekanisme kerja, proses, dan hubungan antar konsep",
        "HOTS": "analisis mendalam, sebab akibat, dan penerapan konsep",
    }

    if level in mapping_sub:
        return mapping_sub[level]

    # Tangkap format "C1 LOTS", "C4 HOTS", dsb
    for sub in mapping_sub:
        if sub in level:
            return mapping_sub[sub]

    return mapping_legacy.get(level, "penjelasan konsep utama")

# proses utama query builder
def build_query(modul: str, topik: str, level: str) -> str:
    """
    Build query untuk semantic search ke FAISS.

    REVISI:
    - Query lebih PENDEK dan SPESIFIK (bukan paragraph panjang)
    - Format: kalimat konseptual singkat tentang topik
    - IndoBERT bekerja lebih baik dengan kalimat 1-2 baris
      yang mengandung kata kunci konsep, bukan instruksi panjang
    """

    level_instruction = map_level_to_instruction(level)

    modul = modul.strip()
    topik = topik.strip()

    # Query padat: langsung menyebut topik + aspek level
    query = (
        f"{topik} adalah konsep dalam {modul}. "
        f"Penjelasan {level_instruction} dari {topik}. "
        f"Karakteristik dan mekanisme {topik}."
    )

    return query.strip()