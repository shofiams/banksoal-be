import re


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_soal(soal):
    """
    Normalisasi untuk ORM Soal object.
    Digunakan saat build vector dari DB.
    """

    # normalisasi soal utama
    pertanyaan = clean_text(soal.pertanyaan)

    opsi_text = []
    for opsi in soal.opsi:
        opsi_text.append(clean_text(opsi.teks))

    return {
        "pertanyaan": pertanyaan,
        "opsi": opsi_text
    }


def combine_soal_and_opsi(soal_dict: dict) -> str:
    """
    Normalisasi untuk dictionary soal.
    Bisa dipakai untuk similarity checking.
    """

    pertanyaan = clean_text(soal_dict["pertanyaan"])

    opsi_texts = []
    for opsi in soal_dict.get("opsi", []):
        opsi_texts.append(clean_text(opsi["text"]))

    return pertanyaan + " opsi: " + ", ".join(opsi_texts)