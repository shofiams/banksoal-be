from app.services.vector.db_loader import get_soal_lama
from app.services.vector.soal_normalizer import normalize_soal
from app.services.embedding.indobert_embedder import _embedder_instance
from app.services.vector.faiss_index import FaissIndex

# tahap 4 recreate 
def build_vector_from_db(id_topik, level_list):

    # memanggil db_laoder = get data soal lama
    soal_list = get_soal_lama(id_topik, level_list)

    if not soal_list:
        raise ValueError("Tidak ada soal ditemukan untuk topik dan level tersebut.")

    vectordb = FaissIndex()
    print(f"Total soal ditemukan: {len(soal_list)}")

    # STEP 1 — kumpulkan semua teks dulu, jangan embed dulu
    combined_texts = []
    metadata_list  = []

    for soal in soal_list:

        # memanggil soal_normalizer
        normalized    = normalize_soal(soal)
        combined_text = (
            normalized["pertanyaan"] +
            " opsi: " +
            ", ".join(normalized["opsi"])
        )
        combined_texts.append(combined_text)
        metadata_list.append({
            "id_soal"        : soal.id,
            "level"          : soal.level_kognitif.value,
            "text_original"  : soal.pertanyaan,
            "text_normalized": combined_text
        })

    # STEP 2 — kirim semua sekaligus, 1 request saja ke HF Spaces
    print(f"Embedding {len(combined_texts)} soal dalam 1 request...")

    # meamnggil indobert_embedder
    vectors = _embedder_instance.embed_batch(combined_texts)

    # STEP 3 — simpan ke FAISS = memanggil faiss index
    for vector, meta in zip(vectors, metadata_list):
        vectordb.add_vector(vector, meta)

    print("Vector database selesai dibangun.")
    return vectordb

# tahap 5 indobert embedder