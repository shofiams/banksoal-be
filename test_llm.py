from app.services.llm.gemini_client import generate_text

prompt = "Buat satu soal biologi tentang sistem pernapasan level LOTS"

hasil = generate_text(prompt)

print(hasil)
