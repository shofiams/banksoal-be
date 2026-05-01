import time

from app.services.recreate.parameter_processor import process_parameter
from app.services.vector.build_from_db import build_vector_from_db
from app.services.recreate.substansi_builder import build_substansi
from app.services.recreate.distribution_validator import validate_distribution

from app.services.llm.gemini_client import generate_text, MAX_SOAL_PER_CALL  # ← generate_text_chunked TIDAK dipakai di sini
from app.services.llm.prompts.recreate_prompt_builder import build_recreate_prompt
from app.services.llm.utils.json_parser import clean_and_parse_json
from app.services.embedding.indobert_embedder import embed_text, tokenizer as indobert_tokenizer


SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

# tahap ke 2 recreate
# menjalankan seluruh proses recreate secara berurutan
# tahap ke 3 parameter processor 
def run_recreate_pipeline(
    id_topik,
    jenjang,
    modul,
    nama_topik,
    jumlah_soal,
    distribusi_level
):
    pipeline_log = {}

    # ── STEP 1: Parameter Processing ──
    print("\n===== STEP 1 - PARAMETER PROCESSING =====")
    step_start = time.time()
    param = process_parameter(id_topik, jenjang, modul, nama_topik, jumlah_soal, distribusi_level)
    step_elapsed = round(time.time() - step_start, 2)
    print(param)

    pipeline_log["step_parameter"] = {
        "label"        : "Input Parameter",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "id_topik"        : param["id_topik"],
            "jenjang"         : param["jenjang"],
            "modul"           : param["modul"],
            "nama_topik"      : param["nama_topik"],
            "jumlah_soal"     : param["jumlah_soal"],
            "distribusi_level": param["distribusi_level"]
        }
    }

    # ── STEP 2: Build Vector DB dari soal lama ──
    print("\n===== STEP 2 - BUILD VECTOR DB =====")
    step_start = time.time()

    dist_keys    = list(param["distribusi_level"].keys())
    is_sub_level = any(k in SUB_TO_LEVEL for k in dist_keys)

    if is_sub_level:
        level_list = list({SUB_TO_LEVEL[k] for k in dist_keys if k in SUB_TO_LEVEL})
    else:
        level_list = dist_keys

    vectordb     = build_vector_from_db(param["id_topik"], level_list)
    step_elapsed = round(time.time() - step_start, 2)

    # REVISI: tampilkan sampel soal lama yang berhasil diambil dari DB
    soal_lama_dari_db = getattr(vectordb, "metadata", [])
    soal_lama_samples = [
        {
            "soal_ke"         : i + 1,
            "preview_soal"    : item.get("text_original", item.get("text_normalized", ""))[:200] + "...",
            "level"           : item.get("level", "-"),
        }
        for i, item in enumerate(soal_lama_dari_db[:3])
    ]
    pipeline_log["step_get_soal_lama"] = {
        "label"              : "Get Data Soal Lama",
        "durasi_detik"       : step_elapsed,
        "total_soal_diambil" : len(soal_lama_dari_db),
        "level_dicari"       : level_list,
        "output_sample"      : soal_lama_samples if soal_lama_samples else {"info": "Soal referensi berhasil diindeks ke FAISS"}
    }

    # ── STEP 3: Embedding Query (nama topik → vektor) ──
    print("\n===== STEP 3 - EMBEDDING QUERY =====")
    step_start = time.time()
    query_vec  = embed_text(param["nama_topik"])
    step_elapsed = round(time.time() - step_start, 2)

    q_tokens    = indobert_tokenizer.tokenize(param["nama_topik"][:200])[:15]
    q_token_ids = indobert_tokenizer.convert_tokens_to_ids(q_tokens)

    pipeline_log["step_embedding_soal"] = {
        "label"        : "Embedding Soal (IndoBERT)",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "input_teks"           : param["nama_topik"],
            "tokens"               : q_tokens,
            "token_ids"            : q_token_ids,
            "output_dimensi"       : int(len(query_vec)),
            "output_vektor_preview": [round(float(v), 6) for v in query_vec[:10]],
        }
    }

    # ── STEP 4: Semantic Retrieval ──
    print("\n===== STEP 4 - SEMANTIC RETRIEVAL =====")
    step_start = time.time()
    results    = vectordb.search(query_vec, k=5)
    step_elapsed = round(time.time() - step_start, 2)

    if not results:
        raise ValueError("Tidak ditemukan soal referensi.")

    # REVISI: tampilkan hasil retrieval FAISS beserta skor similarity
    retrieval_samples = [
        {
            "rank"            : idx + 1,
            "skor_similarity" : round(r.get("score", 0), 4),
            "level"           : r.get("level", "-"),
            "preview_soal"    : r.get("text_original", r.get("text_normalized", ""))[:200] + "...",
        }
        for idx, r in enumerate(results[:3])
        if isinstance(r, dict)
    ]
    pipeline_log["step_vector_db"] = {
        "label"          : "Vector Database (FAISS)",
        "durasi_detik"   : step_elapsed,
        "total_retrieved": len(results),
        "output_sample"  : retrieval_samples
    }

    # ── STEP 5: Pre-Processing ──
    print("\n===== STEP 5 - PRE-PROCESSING =====")
    step_start = time.time()
    dist_info  = {}
    for k, v in param["distribusi_level"].items():
        level_mapped = SUB_TO_LEVEL.get(k, k)
        dist_info[k] = {"jumlah": v, "level_utama": level_mapped}
    step_elapsed = round(time.time() - step_start, 2)

    # REVISI: tampilkan parameter + sampel soal referensi setelah normalisasi
    soal_normalized_samples = [
        {
            "soal_ke"          : idx + 1,
            "teks_normalized"  : r.get("text_normalized", r.get("text_original", ""))[:200] + "...",
            "level"            : r.get("level", "-"),
        }
        for idx, r in enumerate(results[:3])
        if isinstance(r, dict)
    ]
    pipeline_log["step_preprocess"] = {
        "label"        : "Pre-Processing Parameter",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "jenjang"              : param["jenjang"],
            "modul"                : param["modul"],
            "topik"                : param["nama_topik"],
            "distribusi_diproses"  : dist_info,
            "sampel_soal_referensi": soal_normalized_samples
        }
    }

    # ── STEP 6: Build Substansi ──
    print("\n===== STEP 6 - BUILD SUBSTANSI =====")
    step_start = time.time()
    substansi  = build_substansi(results)
    step_elapsed = round(time.time() - step_start, 2)

    pipeline_log["step_substansi"] = {
        "label"        : "Substansi (Soal Referensi)",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "konsep_utama"     : substansi.get("konsep_utama", []),
            "pola_pertanyaan"  : substansi.get("pola_pertanyaan", []),
            "struktur_jawaban" : substansi.get("struktur_jawaban", "-"),
            "level_referensi"  : substansi.get("level_referensi", "-"),
        }
    }

    # ── STEP 7: Context Engineering ──
    print("\n===== STEP 7 - CONTEXT ENGINEERING =====")
    step_start = time.time()
    prompt = build_recreate_prompt(
        substansi=substansi,
        jenjang=param["jenjang"],
        modul=param["modul"],
        nama_topik=param["nama_topik"],
        jumlah_soal=param["jumlah_soal"],
        distribusi_level=param["distribusi_level"]
    )
    step_elapsed = round(time.time() - step_start, 2)

    pipeline_log["step_context_engineering"] = {
        "label"        : "Context Engineering",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "panjang_prompt_karakter": len(prompt),
            "preview_prompt"         : prompt[:500] + "..."
        }
    }

    # ── STEP 8: LLM Generation — CHUNKED PER SUB-LEVEL ──────────────────────
    print("\n===== STEP 8 - LLM GENERATION (PER SUB-LEVEL) =====")
    step_start   = time.time()
    semua_soal   = []
    per_sub_logs = {}

    # generate soal per sub level utama
    for sub_level, jumlah in param["distribusi_level"].items():
        if jumlah == 0:
            continue
 
        level_utama = SUB_TO_LEVEL.get(sub_level, sub_level)
        print(f"  → Generate {sub_level} ({level_utama}): {jumlah} soal")

        # Distribusi untuk satu sub-level ini saja
        distribusi_satu = {sub_level: jumlah}

        soal_sub_level = []
        remaining      = jumlah
        batch_ke       = 0

        while remaining > 0:
            batch    = min(remaining, MAX_SOAL_PER_CALL)
            batch_ke += 1
            print(f"    Batch {batch_ke}: {batch} soal")

            # Build prompt khusus sub-level ini dengan jumlah = batch
            prompt_batch = build_recreate_prompt(
                substansi=substansi,
                jenjang=param["jenjang"],
                modul=param["modul"],
                nama_topik=param["nama_topik"],
                jumlah_soal=batch,
                distribusi_level=distribusi_satu  # ← hanya 1 sub-level
            )

            llm_raw = generate_text(prompt_batch)
            parsed  = clean_and_parse_json(llm_raw)

            if isinstance(parsed, list) and len(parsed) > 0:
                soal_sub_level.extend(parsed)
                remaining -= len(parsed)
                if len(parsed) < batch:
                    print(f"    LLM return {len(parsed)}/{batch}. Loop dihentikan.")
                    break
            else:
                print(f"    Gagal parse JSON pada batch {batch_ke}. Dilewati.")
                break

            if remaining > 0:
                time.sleep(2)  # jeda antar batch

        semua_soal.extend(soal_sub_level[:jumlah])
        per_sub_logs[sub_level] = {
            "diminta"     : jumlah,
            "dihasilkan"  : len(soal_sub_level[:jumlah]),
            "level_utama" : level_utama
        }

    step_elapsed = round(time.time() - step_start, 2)
    # ─────────────────────────────────────────────────────────────────────────

    pipeline_log["step_generate"] = {
        "label"        : "Generate Soal (Gemini AI — per sub-level)",
        "durasi_detik" : step_elapsed,
        "output_sample": {
            "total_soal_dihasilkan": len(semua_soal),
            "detail_per_sub_level" : per_sub_logs,
            "preview_output"       : [
                {
                    "soal_ke"         : i + 1,
                    "preview_soal"    : str(s.get("text_soal", ""))[:150] + "...",
                    "sub_level"       : s.get("sub_level", "-"),
                    "tingkat_kognitif": s.get("tingkat_kognitif", "-")
                }
                for i, s in enumerate(semua_soal[:3])
            ]
        }
    }

    # ── STEP 9: Parse & Validate ──
    print("\n===== STEP 9 - VALIDASI =====")
    try:
        step_start = time.time()
        parsed     = semua_soal

        if not isinstance(parsed, list) or len(parsed) == 0:
            raise ValueError("Tidak ada soal yang berhasil dihasilkan.")

        step_elapsed = round(time.time() - step_start, 2)
        pipeline_log["step_parse_validate"] = {
            "label"                : "Parse & Validasi Output",
            "durasi_detik"         : step_elapsed,
            "total_soal_dihasilkan": len(parsed),
            "output_sample"        : [
                {
                    "soal_ke"         : i + 1,
                    "preview_soal"    : str(s.get("text_soal", ""))[:150] + "...",
                    "sub_level"       : s.get("sub_level", "-"),
                    "tingkat_kognitif": s.get("tingkat_kognitif", "-")
                }
                for i, s in enumerate(parsed[:3])
            ]
        }

        print("\n===== STEP 10 - VALIDATION =====")
        validate_distribution(parsed, param["distribusi_level"])

        return {
            "soal"         : parsed,
            "_pipeline_log": pipeline_log
        }

    except Exception as e:
        print("ERROR:", e)
        raise