from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from app.services.recreate.recreate_pipeline import run_recreate_pipeline

router = APIRouter()

# Mapping sub-level → LOTS/MOTS/HOTS untuk validasi dan konversi
SUB_TO_LEVEL = {
    "C1": "LOTS", "C2": "LOTS",
    "C3": "MOTS",
    "C4": "HOTS", "C5": "HOTS", "C6": "HOTS",
}

ALLOWED_SUB_LEVELS = set(SUB_TO_LEVEL.keys())

#input parameter recreate
class RecreateRequest(BaseModel):
    id_topik: int
    jenjang: str
    modul: str
    nama_topik: str
    jumlah_soal: int
    # Format baru: {"C1": 2, "C3": 1, "C4": 2} — sub-level Bloom's
    # Tetap support format lama {"LOTS": 2, "MOTS": 1, "HOTS": 2} untuk kompatibilitas
    distribusi_level: Dict[str, int]

# tahap ke 1 recreate
@router.post("/recreate")
def recreate_soal(request: RecreateRequest):

    distribusi = request.distribusi_level


    # DETEKSI FORMAT: sub-level (C1-C6) atau legacy (LOTS/MOTS/HOTS)
  
    is_sub_level_format = any(k in ALLOWED_SUB_LEVELS for k in distribusi.keys())
    is_legacy_format    = any(k in {"LOTS", "MOTS", "HOTS"} for k in distribusi.keys())

    if is_sub_level_format and is_legacy_format:
        raise HTTPException(
            status_code=400,
            detail="Jangan campur format sub-level (C1-C6) dengan format lama (LOTS/MOTS/HOTS)."
        )

    # VALIDASI FORMAT SUB-LEVEL (C1-C6)
    if is_sub_level_format:
        # Cek key valid
        for level in distribusi.keys():
            if level not in ALLOWED_SUB_LEVELS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sub-level tidak dikenali: '{level}'. Gunakan C1-C6."
                )

        # Cek nilai negatif
        for level, jumlah in distribusi.items():
            if jumlah < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Distribusi tidak boleh negatif: {level}"
                )

        # Cek total = jumlah_soal
        total = sum(v for v in distribusi.values())
        if total != request.jumlah_soal:
            raise HTTPException(
                status_code=400,
                detail=f"Total distribusi sub-level ({total}) tidak sama dengan jumlah_soal ({request.jumlah_soal})."
            )

        # Hanya kirim sub-level yang > 0 ke pipeline
        distribusi_final = {k: v for k, v in distribusi.items() if v > 0}

    # VALIDASI FORMAT LEGACY (LOTS/MOTS/HOTS)
    else:
        allowed_legacy = {"LOTS", "MOTS", "HOTS"}
        for level in distribusi.keys():
            if level not in allowed_legacy:
                raise HTTPException(
                    status_code=400,
                    detail=f"Level tidak dikenali: '{level}'. Gunakan LOTS/MOTS/HOTS atau C1-C6."
                )

        for level, jumlah in distribusi.items():
            if jumlah < 0:
                raise HTTPException(status_code=400, detail=f"Distribusi tidak boleh negatif: {level}")

        total = sum(v for v in distribusi.values())
        if total != request.jumlah_soal:
            raise HTTPException(
                status_code=400,
                detail=f"Total distribusi ({total}) tidak sama dengan jumlah_soal ({request.jumlah_soal})."
            )

        distribusi_final = {k: v for k, v in distribusi.items() if v > 0}

    # JALANKAN PIPELINE
    hasil = run_recreate_pipeline(
        id_topik=request.id_topik,
        jenjang=request.jenjang,
        modul=request.modul,
        nama_topik=request.nama_topik,
        jumlah_soal=request.jumlah_soal,
        distribusi_level=distribusi_final       # bisa C1-C6 atau LOTS/MOTS/HOTS
    )

    # Pisahkan pipeline_log dari data soal
    pipeline_log = hasil.pop("_pipeline_log", {}) if isinstance(hasil, dict) else {}
    soal_data = hasil.get("soal", hasil) if isinstance(hasil, dict) else hasil

    return {
        "status": "success",
        "data": soal_data,
        "pipeline_log": pipeline_log
    }
# tahap ke 2 recreate_pipeline