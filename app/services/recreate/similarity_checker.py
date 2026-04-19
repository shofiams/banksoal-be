import numpy as np
from app.services.embedding.indobert_embedder import embed_text


def cosine_similarity(vec1, vec2):
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    return np.dot(vec1, vec2) / (
        np.linalg.norm(vec1) * np.linalg.norm(vec2)
    )


def check_similarity_with_references(
    generated_soal_list,
    reference_results,
    threshold=0.85
):
    """
    generated_soal_list : list soal hasil LLM
    reference_results   : hasil retrieval FAISS
    threshold           : batas maksimal kemiripan
    """

    # ===============================
    # Ambil text referensi secara aman
    # ===============================
    reference_texts = []

    for item in reference_results:
        if isinstance(item, dict):
            if "text" in item:
                reference_texts.append(item["text"])
            elif "metadata" in item and "text" in item["metadata"]:
                reference_texts.append(item["metadata"]["text"])

    if not reference_texts:
        # Tidak ada referensi, skip similarity check
        return True

    # ===============================
    # Embed semua referensi
    # ===============================
    reference_embeddings = [
        embed_text(text) for text in reference_texts
    ]

    # ===============================
    # Cek tiap soal hasil generate
    # ===============================
    for soal in generated_soal_list:

        # ⚠ Pastikan pakai key yang benar sesuai output LLM kamu
        gen_text = soal["soal"]

        gen_embedding = embed_text(gen_text)

        for ref_emb in reference_embeddings:
            sim = cosine_similarity(gen_embedding, ref_emb)

            if sim > threshold:
                raise ValueError(
                    f"Soal terlalu mirip dengan referensi (similarity={sim:.2f})"
                )

    return True