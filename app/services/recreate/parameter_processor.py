# Mapping sub-level C1-C6 ke LOTS/MOTS/HOTS
SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

ALLOWED_SUB_LEVELS = set(SUB_TO_LEVEL.keys())
ALLOWED_LEGACY     = {"LOTS", "MOTS", "HOTS"}


def process_parameter(
    id_topik,
    jenjang,
    modul,
    nama_topik,
    jumlah_soal,
    distribusi_level
):
    if not all([id_topik, jenjang, modul, nama_topik, jumlah_soal]):
        raise ValueError("Parameter utama tidak lengkap.")

    jumlah_soal = int(jumlah_soal)

    # ── Deteksi format distribusi ──
    is_sub_level = any(k in ALLOWED_SUB_LEVELS for k in distribusi_level.keys())

    if is_sub_level:
        # Format baru C1-C6 — simpan apa adanya, hanya yang > 0
        normalized = {k: int(v) for k, v in distribusi_level.items()
                      if k in ALLOWED_SUB_LEVELS and int(v) > 0}
        total = sum(normalized.values())
    else:
        # Format lama LOTS/MOTS/HOTS
        normalized = {
            "LOTS": int(distribusi_level.get("LOTS", 0)),
            "MOTS": int(distribusi_level.get("MOTS", 0)),
            "HOTS": int(distribusi_level.get("HOTS", 0)),
        }
        total = sum(normalized.values())

    if total != jumlah_soal:
        raise ValueError(
            f"Total distribusi level ({total}) "
            f"tidak sama dengan jumlah soal ({jumlah_soal})."
        )

    return {
        "id_topik": id_topik,
        "jenjang": jenjang.strip().lower(),
        "modul": modul.strip().lower(),
        "nama_topik": nama_topik.strip().lower(),
        "jumlah_soal": jumlah_soal,
        "distribusi_level": normalized
    }