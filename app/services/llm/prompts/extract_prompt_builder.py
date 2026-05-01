# Deskripsi kognitif per sub-level
BLOOM_DESC = {
    "C1": "C1 - Mengingat (Remember): recall fakta, definisi, urutan, atau prosedur dasar",
    "C2": "C2 - Memahami (Understand): menjelaskan, mengklasifikasikan, merangkum, interpretasi",
    "C3": "C3 - Mengaplikasikan (Apply): menerapkan konsep pada situasi baru atau contoh konkret",
    "C4": "C4 - Menganalisis (Analyze): membedah, membandingkan, sebab-akibat, memilah komponen",
    "C5": "C5 - Mengevaluasi (Evaluate): menilai, membenarkan, mengkritik, memilih solusi terbaik",
    "C6": "C6 - Mencipta (Create): merancang, mengkonstruksi, merumuskan, menghasilkan sesuatu baru",
}

SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

# Panduan struktur soal per sub-level
PANDUAN = {
    "C1": "Pertanyaan recall sederhana: 'Apa yang dimaksud...', 'Sebutkan...', 'Manakah yang termasuk...'",
    "C2": "Pertanyaan pemahaman: 'Jelaskan...', 'Klasifikasikan...', 'Apa perbedaan antara...'",
    "C3": "Pertanyaan aplikasi: 'Jika...maka...', 'Bagaimana cara menerapkan...', skenario konkret",
    "C4": "Skenario analisis: 'Mengapa...', 'Apa yang menyebabkan...', 'Identifikasi hubungan...'",
    "C5": "Evaluasi/penilaian: 'Manakah pendekatan terbaik...', 'Nilai efektivitas...', 'Justifikasi...'",
    "C6": "Kreasi/sintesis: 'Rancang...', 'Bagaimana jika...diubah...', 'Formulasikan solusi...'",
}

# Kata/frasa konstruksi yang DILARANG muncul di soal, jawaban, dan pembahasan
LARANGAN_KONSTRUKSI = """
LARANGAN MUTLAK - KALIMAT KONSTRUKSI:
Soal, pilihan jawaban, DAN pembahasan DILARANG KERAS mengandung kalimat atau frasa konstruksi seperti:
- "Berdasarkan teks/wacana/bacaan di atas..."
- "Perhatikan teks berikut..."
- "Sesuai dengan paragraf..."
- "Menurut bacaan..."
- "Berdasarkan informasi di atas..."
- "Dari wacana tersebut..."
- "Sesuai teks di atas..."
- "Berdasarkan materi..."
- "Sesuai materi di atas..."
- "Berdasarkan dokumen..."
- "Perhatikan gambar/tabel/diagram berikut..."
- "Berdasarkan gambar..."
- Semua frasa sejenis yang merujuk ke sumber eksternal atau teks yang sedang dibaca

SETIAP soal harus MANDIRI dan bisa dijawab tanpa merujuk dokumen asli.
Soal harus menguji PEMAHAMAN KONSEP, bukan kemampuan membaca teks.
"""

# tahap utama context engineering
def build_extract_prompt(
    modul: str,
    topik: str,
    sub_level: str,         # C1, C2, C3, C4, C5, atau C6
    jumlah_soal: int,
    retrieved_chunks: list
) -> str:
    """
    Build prompt untuk 1 sub-level spesifik (C1-C6).
    Dipanggil sekali per sub-level dengan jumlah soal yang diminta.
    """

    context_text = "\n\n".join(
        chunk["content"] for chunk in retrieved_chunks
        if "?" not in chunk["content"]
    )

    level_utama = SUB_TO_LEVEL.get(sub_level, "LOTS")
    deskripsi   = BLOOM_DESC.get(sub_level, sub_level)
    panduan     = PANDUAN.get(sub_level, "")

    prompt = f"""
ANDA ADALAH PAKAR PEMBUAT SOAL PENDIDIKAN (AI EXTRACT MODE).

SUMBER DATA UTAMA:
Dokumen berikut adalah SATU-SATUNYA sumber informasi.
DILARANG menggunakan pengetahuan di luar dokumen.

TUGAS:
Buat {jumlah_soal} soal pilihan ganda level kognitif {sub_level} berdasarkan materi berikut.

SPESIFIKASI:
- Modul         : {modul}
- Topik         : {topik}
- Sub-Level     : {sub_level} ({deskripsi})
- Level Utama   : {level_utama}
- Jumlah Soal   : {jumlah_soal}

PANDUAN MEMBUAT SOAL {sub_level}:
{panduan}

ATURAN PENTING:
1. Gunakan HANYA informasi dari materi yang diberikan.
2. Jangan mengutip kalimat secara mentah.
3. Jangan membuat soal tentang: gambar, tabel, nomor halaman, instruksi pembelajaran.
4. Soal harus bersifat konseptual dan global.
5. Jangan merujuk ke "berdasarkan modul", "gambar berikut", "perhatikan tabel".
6. Semua soal harus bisa dijawab tanpa melihat struktur dokumen asli.
7. Soal WAJIB diparafrase — dilarang menyalin kalimat langsung.
8. Gunakan variasi struktur kalimat.
9. Minimal 60% struktur kalimat berbeda dari teks sumber.
10. Bahasa harus natural, akademik, dan tidak kaku.

ATURAN PEMBAHASAN:
- Menjelaskan mengapa jawaban benar secara ilmiah
- Menjelaskan minimal 1 opsi lain mengapa salah
- Tidak mengulang definisi mentah dari materi
- Tidak menyebut "materi", "teks", atau "informasi di atas"
- Pembahasan berdiri sendiri sebagai penjelasan ilmiah

DISTRIBUSI JAWABAN:
Pastikan jawaban benar tersebar merata di antara opsi A, B, C, D, dan E.

FORMAT OUTPUT WAJIB JSON:
[
  {{
    "soal": "...",
    "opsi": [
      {{"teks": "A. ...", "benar": false}},
      {{"teks": "B. ...", "benar": true}},
      {{"teks": "C. ...", "benar": false}},
      {{"teks": "D. ...", "benar": false}},
      {{"teks": "E. ...", "benar": false}}
    ],
    "pembahasan": "...",
    "level_kognitif": "{level_utama}",
    "sub_level": "{sub_level}"
  }}
]

JANGAN TAMBAHKAN TEKS DI LUAR JSON.

MATERI SUMBER:
{context_text}
"""

    return prompt


# =========================================================
# Fungsi legacy untuk kompatibilitas (LOTS/MOTS/HOTS)
# Dipakai jika ada kode lama yang masih memanggil dengan level="LOTS"
# =========================================================
def build_extract_prompt_legacy(
    modul: str,
    topik: str,
    level: str,           # "LOTS", "MOTS", atau "HOTS"
    jumlah_soal: int,
    retrieved_chunks: list
) -> str:
    # Map ke sub-level representatif
    level_map = {"LOTS": "C2", "MOTS": "C3", "HOTS": "C4"}
    sub = level_map.get(level, "C2")
    return build_extract_prompt(modul, topik, sub, jumlah_soal, retrieved_chunks)
