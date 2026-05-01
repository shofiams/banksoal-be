import re

# tahap ke 3 extract
def clean_text(text: str) -> str:
    """
    Advanced Preprocessing & Structural Filtering
    ================================================
    REVISI:
    - Tambah filter titik-titik panjang (noise daftar isi)
    - Tambah filter metadata penerbit (penyusun, isbn, dll)
    - Tambah filter rasio digit/huruf (baris angka-heavy)
    - Naikkan min panjang baris dari 20 ke 30 karakter
    - Hapus baris yang dominan titik (> 25% karakter adalah titik)
    Tujuan: output = kalimat materi yang bersih dan utuh,
            bukan metadata / noise sampul dokumen.
    """

    # 1. Lowercase
    text = text.lower()

    # 2. HAPUS HEADER MODUL & METADATA PENERBIT
    text = re.sub(r"modul\s+\w+.*?kd\s*[\d\.]+", "", text)

    # Baris "penyusun : nama", "editor : nama", dsb
    text = re.sub(
        r"(penyusun|penerbit|editor|desainer|ilustrasi|kontributor|penelaah|penyelia)\s*[:\-].*",
        "", text
    )

    # Copyright / hak cipta
    text = re.sub(r"(hak cipta|copyright|copyrigth|©|all rights reserved).*", "", text)

    # ISBN / nomor katalog
    text = re.sub(r"isbn[\s\-:]*[\d\-]+", "", text)

    # Cetakan ke-n / edisi revisi
    text = re.sub(r"(cetakan|edisi)\s+(ke[\s\-]?\w+|revisi).*", "", text)

    # 3. HAPUS NOMOR HALAMAN & TITIK-TITIK PANJANG
    text = re.sub(r"\bhalaman\s*\d+\b", "", text)
    text = re.sub(r"\bpage\s*\d+\b", "", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Hapus titik-titik panjang (noise daftar isi / spasi visual)
    text = re.sub(r"\.{3,}", " ", text)

    # Hapus pola "Judul Bab ............... 12" (baris daftar isi)
    text = re.sub(r"\w[\w\s]+\s{2,}\d+\s*$", "", text, flags=re.MULTILINE)

    # 4. HAPUS GAMBAR / TABEL / LINK
    text = re.sub(r"\bgambar\s*\d+.*", "", text)
    text = re.sub(r"\btabel\s*\d+.*", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    # 5. HAPUS PILIHAN JAWABAN (a. b. c. d. e.)
    text = re.sub(r"\b[a-e]\.\s*", "", text)

    # 6. KEYWORD FILTERING STRUKTURAL (PER BARIS)
    structural_keywords = [
        # Struktur dokumen
        "identitas modul", "pendahuluan", "peta konsep",
        "petunjuk penggunaan", "kompetensi dasar", "tujuan pembelajaran",
        "daftar isi", "kata pengantar", "glosarium", "rangkuman",
        "direktorat", "dikdas", "dikmen",
        # Metadata penerbit / institusi
        "penyusun", "kementerian pendidikan", "kemendikbud",
        "diterbitkan oleh", "cetakan", "isbn",
        "deskripsi singkat", "alokasi waktu", "kegiatan pembelajaran",
        "materi pokok", "sub materi",
        # Evaluasi
        "evaluasi", "soal latihan", "soal evaluasi", "latihan soal",
        "kunci jawaban", "pembahasan", "pedoman penskoran",
        "konversi tingkat penguasaan",
        # Instruksional
        "pilihlah jawaban", "perhatikan gambar", "cocokkanlah",
        "hitunglah", "gunakan rumus berikut", "jawaban yang benar",
        "kerjakan soal", "setelah mempelajari", "setelah membaca",
        "buatlah kliping", "jawablah pertanyaan",
    ]

    lines = text.split("\n")
    filtered_lines = []


    # tahap utama Pre-Processing
    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Skip baris mengandung keyword struktural
        if any(keyword in line for keyword in structural_keywords):
            continue

        # Skip baris terlalu pendek (noise, header satu kata, nomor)
        if len(line) < 30:
            continue

        # Skip baris yang dominan titik (pola daftar isi)
        dot_ratio = line.count(".") / len(line)
        if dot_ratio > 0.25:
            continue

        # Skip baris yang digit-nya jauh lebih banyak dari huruf
        digit_count = sum(1 for c in line if c.isdigit())
        alpha_count = sum(1 for c in line if c.isalpha())
        if alpha_count > 0 and digit_count / alpha_count > 0.4:
            continue

        filtered_lines.append(line)

    text = " ".join(filtered_lines)

    # 7. HAPUS ANGKA BERDIRI SENDIRI
    text = re.sub(r"\b\d+\b", "", text)

    # 8. HAPUS SIMBOL ANEH
    #    (pertahankan titik & koma agar kalimat tetap utuh)
    text = re.sub(r"[^\w\s\.\,\-]", " ", text)

    # 9. NORMALISASI SPASI
    text = re.sub(r"\s+", " ", text).strip()

    return text

# tahap ke 4 chunker.py