import random
import logging


def randomize_option_positions(question: dict) -> dict:
    """
    Acak urutan opsi dan reset label A–E.
    Pastikan tetap hanya 1 jawaban benar.
    """

    opsi = question.get("opsi", [])

    if not opsi or not isinstance(opsi, list):
        return question

    # Pastikan hanya 1 jawaban benar
    benar_list = [o for o in opsi if o.get("benar") is True]
    if len(benar_list) != 1:
        logging.warning("Jawaban benar tidak tepat 1 saat randomisasi.")
        return question

    # Acak opsi
    random.shuffle(opsi)

    # Reset label A-E
    labels = ["A", "B", "C", "D", "E"]

    for i, o in enumerate(opsi):
        teks = o.get("teks", "")

        # Hapus label lama jika ada
        if "." in teks:
            teks = teks.split(".", 1)[1].strip()

        if i < len(labels):
            o["teks"] = f"{labels[i]}. {teks}"
        else:
            # Jika opsi > 5 (jarang terjadi)
            o["teks"] = teks

    question["opsi"] = opsi
    return question

# validasi soal utama
def validate_and_fix_questions(questions: list, expected_level: str) -> list:
    """
    Validasi dan normalisasi struktur soal:

    - Harus ada field wajib
    - Minimal 4 opsi
    - Tepat 1 jawaban benar
    - Level disesuaikan
    - Randomisasi opsi
    """

    validated = []

    if not isinstance(questions, list):
        logging.warning("Output LLM bukan list.")
        return []

    for q in questions:
        try:
            # =========================
            # VALIDASI FIELD WAJIB
            # =========================
            if not isinstance(q, dict):
                logging.warning("Format soal bukan dict.")
                continue

            if not all(k in q for k in ["soal", "opsi", "pembahasan"]):
                logging.warning("Soal tidak lengkap, dilewati.")
                continue

            if not isinstance(q["soal"], str) or len(q["soal"].strip()) < 15:
                logging.warning("Teks soal terlalu pendek.")
                continue

            opsi = q["opsi"]

            # =========================
            # VALIDASI OPSI
            # =========================
            if not isinstance(opsi, list) or len(opsi) < 4:
                logging.warning("Opsi kurang dari 4, dilewati.")
                continue

            # Pastikan hanya 1 jawaban benar
            correct_count = sum(1 for o in opsi if o.get("benar") is True)

            if correct_count != 1:
                logging.warning("Jumlah jawaban benar tidak = 1.")
                continue

            # =========================
            # SET LEVEL SESUAI REQUEST
            # =========================
            q["level_kognitif"] = expected_level

            # =========================
            # RANDOMISASI OPSI
            # =========================
            q = randomize_option_positions(q)

            validated.append(q)

        except Exception as e:
            logging.error(f"Error validasi soal: {e}")
            continue

    return validated
