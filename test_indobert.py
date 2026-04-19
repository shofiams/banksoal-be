from app.services.embedding.indobert_embedder import embed_text

print("⏳ Mulai download IndoBERT (jika belum ada)...")
vec = embed_text("Ini contoh soal biologi tentang sistem pernapasan")
print("✅ IndoBERT siap, panjang embedding:", len(vec))
