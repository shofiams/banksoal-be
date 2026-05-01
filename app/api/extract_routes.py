from fastapi import APIRouter, UploadFile, File, Form
import os
import uuid
import logging
import time

from app.services.extract import parser, preprocessor, chunker
from app.services.vector.faiss_index import FaissIndex
from app.services.extract.query_builder import build_query
from app.services.embedding.indobert_embedder import IndoBERTEmbedder, tokenizer as indobert_tokenizer
from app.services.llm.prompts.extract_prompt_builder import build_extract_prompt
from app.services.llm.gemini_client import generate_text_chunked, MAX_SOAL_PER_CALL  # ← BERUBAH
from app.services.llm.utils.json_parser import clean_and_parse_json
from app.services.llm.utils.soal_validator import validate_and_fix_questions

router = APIRouter(prefix="/extract", tags=["AI Extract"])

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

embedder = IndoBERTEmbedder()
faiss_store = {}

SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

ALLOWED_SUB_LEVELS = list(SUB_TO_LEVEL.keys())


def is_valid_content_chunk(text: str) -> bool:
    if not text or len(text) < 150:
        return False
    if text.count("?") > 1:
        return False
    blacklist_phrases = [
        "mata pelajaran","alokasi waktu","judul modul","kegiatan pembelajaran",
        "untuk mengukur kemampuan","cobalah kalian","buatlah kliping","pilihlah jawaban",
        "perhatikan gambar","apakah saya dapat","jawablah","soal berikut","evaluasi",
        "kunci jawaban","pedoman penskoran","konversi tingkat penguasaan",
        "modul ini terbagi","petunjuk penggunaan","kompetensi dasar"
    ]
    if any(phrase in text.lower() for phrase in blacklist_phrases):
        return False
    return True


def remove_duplicates(questions):
    seen = set()
    unique = []
    for q in questions:
        key = q.get("soal") or q.get("text_soal")
        if key and key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


# ==========================================
# UPLOAD ONLY
# ==========================================
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    logging.info("===== MULAI PROSES UPLOAD & INDEX =====")
    file_id   = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    pages         = parser.parse_document(file_path)
    cleaned_pages = [(pn, preprocessor.clean_text(t)) for pn, t in pages]

    all_chunks = []
    for page_num, text in cleaned_pages:
        for chunk in chunker.chunk_text(text=text, page_number=page_num, file_id=file_id, chunk_size=500, overlap=200):
            if is_valid_content_chunk(chunk["content"]):
                all_chunks.append(chunk)

    if not all_chunks:
        return {"error": "Tidak ada materi valid setelah filtering."}

    texts      = [c["content"] for c in all_chunks]
    embeddings = embedder.embed_batch(texts, batch_size=64)

    faiss_index = FaissIndex(dimension=768, metric="cosine")
    for vector, meta in zip(embeddings, all_chunks):
        faiss_index.add_vector(vector, meta)

    faiss_store[file_id] = faiss_index

    return {"file_id": file_id, "total_pages": len(pages), "total_valid_chunks": len(all_chunks)}


# tahap input parameter

@router.post("/full-generate")
async def full_generate(
    file: UploadFile = File(...),
    modul: str = Form(...),
    topik: str = Form(...),
    jumlah_soal: int = Form(...),
    c1: int = Form(0),
    c2: int = Form(0),
    c3: int = Form(0),
    c4: int = Form(0),
    c5: int = Form(0),
    c6: int = Form(0),
    lots: int = Form(0),
    mots: int = Form(0),
    hots: int = Form(0),
):
    use_sub_level = (c1 + c2 + c3 + c4 + c5 + c6) > 0
    use_legacy    = (lots + mots + hots) > 0

    if use_sub_level:
        distribusi_sub = {"C1":c1,"C2":c2,"C3":c3,"C4":c4,"C5":c5,"C6":c6}
        total = sum(distribusi_sub.values())
        if total != jumlah_soal:
            return {"error": f"Total distribusi sub-level ({total}) harus sama dengan jumlah_soal ({jumlah_soal})"}
    elif use_legacy:
        distribusi_sub = {"C1":0,"C2":lots,"C3":mots,"C4":hots,"C5":0,"C6":0}
        total = lots + mots + hots
        if total != jumlah_soal:
            return {"error": f"Total distribusi ({total}) harus sama dengan jumlah_soal ({jumlah_soal})"}
    else:
        return {"error": "Harap isi distribusi level kognitif (c1-c6 atau lots/mots/hots)."}

    # ── STEP 1: Parse dokumen ──
    pipeline_log = {}
    step_start = time.time()

    file_id   = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    logging.info("===== MULAI FULL GENERATE PIPELINE =====")

    pages = parser.parse_document(file_path)
    step_elapsed = round(time.time() - step_start, 2)

    # REVISI: skip halaman sampul/daftar isi (teks pendek < 200 karakter),
    # ambil 3 halaman pertama yang punya isi konten cukup.
    content_pages = [(pn, text) for pn, text in pages if len(text.strip()) > 200]
    parser_samples = [
        {
            "halaman"         : pn,
            "jumlah_karakter" : len(text.strip()),
            "preview"         : text.strip()[:400] + ("..." if len(text.strip()) > 400 else "")
        }
        for pn, text in content_pages[:3]
    ]
    pipeline_log["step_parse"] = {
        "label"                 : "Parse Dokumen",
        "durasi_detik"          : step_elapsed,
        "total_halaman"         : len(pages),
        "halaman_berisi_konten" : len(content_pages),
        "output_sample"         : parser_samples
    }

    # ── STEP 2: Preprocessing ──
    step_start = time.time()
    cleaned_pages = [(pn, preprocessor.clean_text(t)) for pn, t in pages]
    step_elapsed = round(time.time() - step_start, 2)

    # REVISI: ambil halaman yang sudah bersih dan punya isi,
    # skip halaman yang setelah di-clean hasilnya kosong/terlalu pendek.
    clean_content_pages = [(pn, text) for pn, text in cleaned_pages if len(text.strip()) > 100]
    preprocess_samples = [
        {
            "halaman"         : pn,
            "jumlah_karakter" : len(text.strip()),
            "preview"         : text.strip()[:400] + ("..." if len(text.strip()) > 400 else "")
        }
        for pn, text in clean_content_pages[:3]
    ]
    pipeline_log["step_preprocess"] = {
        "label"                  : "Pre-Processing",
        "durasi_detik"           : step_elapsed,
        "total_halaman"          : len(cleaned_pages),
        "halaman_lolos_filter"   : len(clean_content_pages),
        "output_sample"          : preprocess_samples
    }

    # ── STEP 3: Chunking ──
    step_start = time.time()
    all_chunks = []
    raw_chunk_count = 0
    for page_num, text in cleaned_pages:
        raw_chunks = chunker.chunk_text(text=text, page_number=page_num, file_id=file_id, chunk_size=500, overlap=200)
        raw_chunk_count += len(raw_chunks)
        for chunk in raw_chunks:
            if is_valid_content_chunk(chunk["content"]):
                all_chunks.append(chunk)
    step_elapsed = round(time.time() - step_start, 2)

    chunk_samples = [
        {
            "chunk_id": c["chunk_id"],
            "halaman" : c["page"],
            "panjang" : len(c["content"]),
            "preview" : c["content"][:250] + ("..." if len(c["content"]) > 250 else "")
        }
        for c in all_chunks[:5]
    ]
    pipeline_log["step_chunking"] = {
        "label"            : "Chunking",
        "durasi_detik"     : step_elapsed,
        "total_chunk_raw"  : raw_chunk_count,
        "total_chunk_valid": len(all_chunks),
        "chunk_size"       : 500,
        "overlap"          : 200,
        "output_sample"    : chunk_samples
    }

    if not all_chunks:
        return {"error": "Tidak ada materi valid setelah filtering.", "pipeline_log": pipeline_log}

    # ── STEP 4: Embedding ──
    step_start = time.time()
    texts      = [c["content"] for c in all_chunks]
    embeddings = embedder.embed_batch(texts, batch_size=64)
    step_elapsed = round(time.time() - step_start, 2)

    embedding_samples = []
    for i in range(min(3, len(embeddings))):
        teks      = texts[i]
        tokens    = indobert_tokenizer.tokenize(teks[:200])[:15]
        token_ids = indobert_tokenizer.convert_tokens_to_ids(tokens)
        vektor    = embeddings[i]
        embedding_samples.append({
            "chunk_id"             : all_chunks[i]["chunk_id"],
            "input_teks"           : teks[:150] + ("..." if len(teks) > 150 else ""),
            "tokens"               : tokens,
            "token_ids"            : token_ids,
            "output_dimensi"       : int(len(vektor)),
            "output_vektor_preview": [round(float(v), 6) for v in vektor[:10]],
        })

    pipeline_log["step_embedding"] = {
        "label"         : "Embedding (IndoBERT)",
        "durasi_detik"  : step_elapsed,
        "total_vektor"  : len(embeddings),
        "dimensi_vektor": int(len(embeddings[0])) if len(embeddings) > 0 else 0,
        "output_sample" : embedding_samples
    }

    # ── STEP 5: Build Vector DB ──
    step_start = time.time()
    faiss_index = FaissIndex(dimension=768, metric="cosine")
    for vector, meta in zip(embeddings, all_chunks):
        faiss_index.add_vector(vector, meta)
    step_elapsed = round(time.time() - step_start, 2)

    # REVISI: tampilkan 3 sampel chunk yang benar-benar tersimpan di FAISS
    faiss_stored_samples = [
        {
            "chunk_id"   : all_chunks[i]["chunk_id"],
            "halaman"    : all_chunks[i]["page"],
            "isi_chunk"  : all_chunks[i]["content"][:200] + ("..." if len(all_chunks[i]["content"]) > 200 else ""),
            "vektor_preview": [round(float(v), 6) for v in embeddings[i][:5]],
        }
        for i in range(min(3, len(all_chunks)))
    ]
    pipeline_log["step_vectordb"] = {
        "label"                  : "Vector DB (FAISS)",
        "durasi_detik"           : step_elapsed,
        "total_vektor_tersimpan" : len(all_chunks),
        "metric"                 : "cosine similarity",
        "dimensi_vektor"         : 768,
        "output_sample"          : faiss_stored_samples
    }

    # ── Generate per sub-level ──
    results_per_level = {}
    per_level_logs    = {}

    for sub_level, jumlah in distribusi_sub.items():
        if jumlah == 0:
            continue

        level_utama = SUB_TO_LEVEL[sub_level]
        logging.info(f"Generate {sub_level} ({level_utama}) sebanyak {jumlah} soal")
        level_log = {}

        # STEP 6: Query Builder
        step_start = time.time()
        query      = build_query(modul, topik, f"{sub_level} {level_utama}")
        step_elapsed = round(time.time() - step_start, 2)
        level_log["step_query_builder"] = {
            "label"        : f"Query Builder ({sub_level})",
            "durasi_detik" : step_elapsed,
            "output_sample": {"query": query}
        }

        # STEP 7: Embedding Query
        step_start      = time.time()
        query_embedding = embedder.embed_query(query)
        step_elapsed    = round(time.time() - step_start, 2)
        q_tokens    = indobert_tokenizer.tokenize(query[:200])[:15]
        q_token_ids = indobert_tokenizer.convert_tokens_to_ids(q_tokens)
        level_log["step_embedding_query"] = {
            "label"        : f"Embedding Query ({sub_level})",
            "durasi_detik" : step_elapsed,
            "output_sample": {
                "input_query"          : query[:150] + "...",
                "tokens"               : q_tokens,
                "token_ids"            : q_token_ids,
                "output_dimensi"       : int(len(query_embedding)),
                "output_vektor_preview": [round(float(v), 6) for v in query_embedding[:10]],
            }
        }

        # STEP 8: Semantic Search
        step_start = time.time()
        retrieved  = faiss_index.search(query_embedding, k=8)
        step_elapsed = round(time.time() - step_start, 2)
        search_samples = [
            {
                "rank"            : idx + 1,
                "skor_similarity" : round(r.get("score", 0), 4) if isinstance(r, dict) else 0,
                "halaman"         : r.get("page", "-") if isinstance(r, dict) else "-",
                "preview"         : (r.get("content","") if isinstance(r, dict) else str(r))[:200] + "..."
            }
            for idx, r in enumerate(retrieved[:5])
        ]
        level_log["step_semantic_search"] = {
            "label"          : f"Semantic Search ({sub_level})",
            "durasi_detik"   : step_elapsed,
            "total_retrieved": len(retrieved),
            "output_sample"  : search_samples
        }

        # ── STEP 9: Generate soal — CHUNKED ──────────────────────────────────
        # PERUBAHAN: Dulu 1 LLM call untuk semua soal → sekarang dipecah
        # jadi batch kecil (MAX_SOAL_PER_CALL) supaya tidak timeout.
        # Karena loop ini per sub-level, distribusi kognitif tetap terjaga.
        # ─────────────────────────────────────────────────────────────────────
        total_start = time.time()

        # Closure: tangkap sub_level & retrieved dari iterasi saat ini
        _sub   = sub_level
        _retr  = retrieved

        def _build_prompt(jumlah_soal, sub_level=_sub, retrieved_chunks=_retr):
            return build_extract_prompt(
                modul=modul,
                topik=topik,
                sub_level=sub_level,
                jumlah_soal=jumlah_soal,
                retrieved_chunks=retrieved_chunks
            )

        raw_questions = generate_text_chunked(
            build_prompt_fn=_build_prompt,
            total_soal=jumlah,
            chunk_size=MAX_SOAL_PER_CALL
        )
        validated     = validate_and_fix_questions(raw_questions, expected_level=level_utama)
        final_questions = remove_duplicates(validated)[:jumlah]
        elapsed = round(time.time() - total_start, 2)
        # ─────────────────────────────────────────────────────────────────────

        level_log["step_generate"] = {
            "label"            : f"Generate Soal AI ({sub_level})",
            "durasi_detik"     : elapsed,
            "jumlah_dihasilkan": len(final_questions),
            "jumlah_diminta"   : jumlah,
            "output_sample"    : [
                {
                    "soal_ke"     : i + 1,
                    "preview_soal": q.get("soal", q.get("text_soal", ""))[:150] + "...",
                    "level"       : q.get("level_kognitif", level_utama),
                    "sub_level"   : q.get("sub_level", sub_level)
                }
                for i, q in enumerate(final_questions[:3])
            ]
        }

        per_level_logs[sub_level] = level_log

        if level_utama not in results_per_level:
            results_per_level[level_utama] = {"jumlah": 0, "generated_soal": []}

        results_per_level[level_utama]["jumlah"]         += jumlah
        results_per_level[level_utama]["generated_soal"].extend(final_questions)

    results_per_level["_pipeline_log"] = {
        **pipeline_log,
        "per_level": per_level_logs
    }

    return results_per_level