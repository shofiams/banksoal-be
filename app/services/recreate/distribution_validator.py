# Mapping sub-level C1-C6 ke LOTS/MOTS/HOTS
SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}


def validate_distribution(generated_soal_list, distribusi_target):
    """
    Validasi distribusi soal yang dihasilkan terhadap target.
    Mendukung format sub-level C1-C6 maupun format lama LOTS/MOTS/HOTS.
    """

    # Deteksi apakah distribusi_target pakai C1-C6 atau LOTS/MOTS/HOTS
    is_sub_level = any(k in SUB_TO_LEVEL for k in distribusi_target.keys())

    if is_sub_level:
        # ── Hitung sub_level dari hasil generate ──
        count_sub = {k: 0 for k in SUB_TO_LEVEL}
        for soal in generated_soal_list:
            sub = soal.get("sub_level", "").upper()
            if sub in count_sub:
                count_sub[sub] += 1
            else:
                # Fallback: coba derive dari tingkat_kognitif jika sub_level kosong
                tk = soal.get("tingkat_kognitif", "").upper()
                if tk == "LOTS":
                    count_sub["C1"] += 1
                elif tk == "MOTS":
                    count_sub["C3"] += 1
                elif tk == "HOTS":
                    count_sub["C4"] += 1

        for sub, target in distribusi_target.items():
            if target == 0:
                continue
            hasil = count_sub.get(sub, 0)
            if hasil != target:
                raise ValueError(
                    f"Distribusi {sub} tidak sesuai. "
                    f"Target: {target}, Dihasilkan: {hasil}"
                )

    else:
        # ── Format lama LOTS/MOTS/HOTS ──
        count_result = {"LOTS": 0, "MOTS": 0, "HOTS": 0}

        for soal in generated_soal_list:
            level = soal.get("tingkat_kognitif", "").upper()
            if level in count_result:
                count_result[level] += 1

        for level, target in distribusi_target.items():
            if target == 0:
                continue
            if count_result.get(level, 0) != target:
                raise ValueError(
                    f"Distribusi {level} tidak sesuai. "
                    f"Target: {target}, Dihasilkan: {count_result.get(level, 0)}"
                )

    return True