from app.services.vector.db_loader import get_soal_lama
from app.services.vector.soal_normalizer import normalize_soal
from app.services.embedding.indobert_embedder import embed_text
from app.services.vector.faiss_index import FaissIndex


def build_vector_from_db(id_topik, level_list):
    """
    Tahap Pre-Processing AI Recreate:
    1. Get Data Soal Lama
    2. Normalisasi Soal
    3. Embedding Soal
    4. Simpan ke Vector Database (FAISS)
    """

    # === GET DATA SOAL LAMA ===
    soal_list = get_soal_lama(id_topik, level_list)

    if not soal_list:
        raise ValueError("Tidak ada soal ditemukan untuk topik dan level tersebut.")

    vectordb = FaissIndex()

    print(f"Total soal ditemukan: {len(soal_list)}")

    # === PROSES NORMALISASI + EMBEDDING ===
    for soal in soal_list:
        normalized = normalize_soal(soal)

        combined_text = (
            normalized["pertanyaan"] +
            " opsi: " +
            ", ".join(normalized["opsi"])
        )

        vector = embed_text(combined_text)

        vectordb.add_vector(vector, {
            "id_soal": soal.id,
            "level": soal.level_kognitif.value,
            "text_original": soal.pertanyaan,
            "text_normalized": combined_text
        })

    print("Vector database selesai dibangun.")

    return vectordb