import json

BLOOM_DESC = {
    "C1": "C1 - Mengingat (Remember): recall fakta, definisi, urutan, atau prosedur dasar",
    "C2": "C2 - Memahami (Understand): menjelaskan, mengklasifikasikan, merangkum, atau menginterpretasikan konsep",
    "C3": "C3 - Mengaplikasikan (Apply): menerapkan prosedur atau konsep pada situasi baru atau contoh konkret",
    "C4": "C4 - Menganalisis (Analyze): membedah, membandingkan, mengidentifikasi hubungan sebab-akibat, atau memilah komponen",
    "C5": "C5 - Mengevaluasi (Evaluate): menilai, membenarkan, mengkritik, atau memilih solusi terbaik berdasarkan kriteria",
    "C6": "C6 - Mencipta (Create): merancang, mengkonstruksi, merumuskan, atau menghasilkan sesuatu yang baru",
}

SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

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
- "Berdasarkan soal referensi..."
- "Sesuai dengan soal di atas..."
- Semua frasa sejenis yang merujuk ke sumber eksternal atau referensi

SETIAP soal harus MANDIRI dan bisa dijawab tanpa konteks tambahan.
Soal menguji PEMAHAMAN KONSEP secara langsung, bukan kemampuan membaca/referensi teks.
"""


def build_recreate_prompt(
    substansi,
    jenjang,
    modul,
    nama_topik,
    jumlah_soal,
    distribusi_level
):
    distribusi_lines = []
    for sub, jumlah in distribusi_level.items():
        if jumlah > 0:
            desc = BLOOM_DESC.get(sub, sub)
            distribusi_lines.append(f"  - {jumlah} soal {desc}")

    distribusi_text = "\n".join(distribusi_lines)

    panduan_lines = []
    for sub, jumlah in distribusi_level.items():
        if jumlah <= 0:
            continue
        if sub in ("C1", "C2"):
            panduan_lines.append(
                f"  [{sub}] Gunakan pertanyaan recall/pemahaman: 'Apa yang dimaksud...', "
                f"'Sebutkan...', 'Jelaskan konsep...', 'Klasifikasikan...' "
                f"→ buat {jumlah} soal."
            )
        elif sub == "C3":
            panduan_lines.append(
                f"  [{sub}] Gunakan pertanyaan aplikasi: 'Jika...maka...', 'Bagaimana cara...', "
                f"'Terapkan konsep...pada kasus...' → buat {jumlah} soal."
            )
        elif sub == "C4":
            panduan_lines.append(
                f"  [{sub}] Gunakan skenario analisis: 'Mengapa...', 'Apa perbedaan...', "
                f"'Identifikasi komponen yang...' → buat {jumlah} soal."
            )
        elif sub == "C5":
            panduan_lines.append(
                f"  [{sub}] Gunakan evaluasi: 'Manakah pendekatan terbaik...', "
                f"'Nilai efektivitas...', 'Justifikasi keputusan...' → buat {jumlah} soal."
            )
        elif sub == "C6":
            panduan_lines.append(
                f"  [{sub}] Gunakan kreasi/sintesis: 'Rancang...', 'Bagaimana jika...', "
                f"'Konstruksi solusi...', 'Formulasikan...' → buat {jumlah} soal."
            )

    panduan_text = "\n".join(panduan_lines)

    prompt = f"""
ANDA ADALAH SISTEM AUTOMATIC QUESTION GENERATION (AQG) BERBASIS RAG.

PERAN ANDA:
Menghasilkan variasi soal baru berdasarkan substansi referensi,
tanpa menyalin soal lama secara langsung.

========================================
KONTEKS SUBSTANSI (HASIL RETRIEVAL)
========================================
Gunakan substansi berikut sebagai referensi pola dan konsep:

{json.dumps(substansi, indent=2)}

Catatan:
- Jangan menyalin teks soal lama.
- Gunakan hanya konsep dan pola pertanyaannya.
- Bangun variasi baru dengan struktur berbeda namun materi tetap relevan.

========================================
METADATA PARAMETER
========================================
Jenjang        : {jenjang}
Mata Pelajaran : {modul}
Topik          : {nama_topik}
Jumlah Soal    : {jumlah_soal}

========================================
DISTRIBUSI LEVEL KOGNITIF (BLOOM'S TAXONOMY)
========================================
Buat soal dengan distribusi SUB-LEVEL berikut secara TEPAT:

{distribusi_text}

Panduan per sub-level:
{panduan_text}

PENTING:
- Setiap soal WAJIB mencantumkan field "sub_level" sesuai C1-C6 yang diminta.
- "tingkat_kognitif" diisi LOTS/MOTS/HOTS berdasarkan mapping:
    C1,C2 → LOTS | C3 → MOTS | C4,C5,C6 → HOTS
- Pastikan JUMLAH soal per sub-level TEPAT sesuai distribusi di atas.

{LARANGAN_KONSTRUKSI}

========================================
ATURAN GENERASI
========================================
1. Setiap soal harus:
   - Sinkron antara pertanyaan, jawaban, dan pembahasan.
   - Memiliki 5 pilihan (A–E).
   - Hanya 1 jawaban benar.
   - Distraktor logis dan relevan.
2. Gunakan variasi struktur kalimat.
3. Hindari pengulangan frasa dari substansi.
4. Jangan menambahkan materi di luar topik.
5. Sesuaikan tingkat berpikir dengan sub-level kognitif yang diminta (C1–C6).
6. Jangan memberikan teks di luar format JSON.
7. Pembahasan DILARANG dimulai dengan frasa konstruksi seperti "Berdasarkan...", "Sesuai teks...", dll.
8. Pembahasan harus berdiri sendiri sebagai penjelasan ilmiah yang mandiri.

========================================
FORMAT OUTPUT (WAJIB JSON ARRAY)
========================================
[
  {{
    "text_soal": "...",
    "pilihan": [
      {{"label":"A","text":"...","is_correct":false}},
      {{"label":"B","text":"...","is_correct":true}},
      {{"label":"C","text":"...","is_correct":false}},
      {{"label":"D","text":"...","is_correct":false}},
      {{"label":"E","text":"...","is_correct":false}}
    ],
    "pembahasan": "...",
    "sub_level": "C1",
    "tingkat_kognitif": "LOTS"
  }}
]

JANGAN TAMBAHKAN PENJELASAN DI LUAR JSON.
"""

    return prompt
