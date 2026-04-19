from app.services.recreate.build_vector_from_db import build_vector_from_db
from app.services.recreate.substansi_builder import build_substansi
from app.services.embedding.indobert_embedder import embed_text


id_topik = 1
level_list = ["LOTS", "MOTS"]

# 1️⃣ Build vector DB dari database
vectordb = build_vector_from_db(id_topik, level_list)

# 2️⃣ Buat embedding query
query_vec = embed_text("soal tentang alveolus")

# 3️⃣ Ambil hasil semantic search
results = vectordb.search(query_vec, k=3)

print("Hasil retrieval:")
for r in results:
    print(r)

# 4️⃣ Bangun substansi
substansi = build_substansi(results)

print("\nSubstansi:")
for s in substansi:
    print(s)
