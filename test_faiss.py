from app.services.recreate.embedder import embed_text
from app.services.vector.faiss_index import FaissIndex

# Buat index
faiss_index = FaissIndex()

# Tambah beberapa contoh
texts = [
    "soal tentang sistem pernapasan manusia",
    "soal tentang struktur bakteri",
    "soal tentang fotosintesis"
]

for i, text in enumerate(texts):
    vec = embed_text(text)
    faiss_index.add_vector(vec, {"id": i, "text": text})

# Query
query_vec = embed_text("materi paru paru manusia")
results = faiss_index.search(query_vec, k=2)

print("Hasil semantic search:")
for r in results:
    print(r)
