"""
Route PENGUJIAN KUALITAS SOAL — hanya untuk kebutuhan akademik (validasi dosen).
Saat penyerahan ke mitra:
  - Hapus file ini
  - Hapus baris include router di app/api/v1/router.py
  - Hapus frontend: src/features/pengujian/
  - Hapus route /pengujian di AppRouter.jsx
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.pengujian import PengujianPenguji, EvaluasiSoal
from app.models.soal import Soal

router = APIRouter(prefix="/pengujian", tags=["Pengujian Kualitas Soal"])

SKOR_MAKS_PER_SOAL = 20  # 5 aspek x skala maks 4


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================================================
# SCHEMA
# ================================================================

class PengujiCreate(BaseModel):
    nama: str
    pendidikan_terakhir: str
    asal_sekolah: str
    mata_pelajaran: str


class EvaluasiItem(BaseModel):
    id_soal: int
    kode_soal: str
    kesesuaian_soal: int
    kebenaran_jawaban: int
    kebenaran_pembahasan: int
    kesesuaian_level_kognitif: int
    konstruksi_soal: int
    level_kognitif_sistem: str
    level_kognitif_evaluator: str
    catatan: Optional[str] = None

    @validator("kesesuaian_soal", "kebenaran_jawaban", "kebenaran_pembahasan",
               "kesesuaian_level_kognitif", "konstruksi_soal")
    def nilai_harus_1_4(cls, v):
        if v < 1 or v > 4:
            raise ValueError("Nilai harus antara 1 sampai 4")
        return v

    @validator("level_kognitif_sistem", "level_kognitif_evaluator")
    def level_harus_valid(cls, v):
        if v.upper() not in {"LOTS", "MOTS", "HOTS"}:
            raise ValueError("Level kognitif harus LOTS, MOTS, atau HOTS")
        return v.upper()


class SubmitEvaluasiRequest(BaseModel):
    penguji: PengujiCreate
    evaluasi_list: List[EvaluasiItem]
    judul_soal: Optional[str] = None
    soal_snapshot: Optional[List[Dict[str, Any]]] = None

    @validator("evaluasi_list")
    def tidak_boleh_kosong(cls, v):
        if not v:
            raise ValueError("evaluasi_list tidak boleh kosong")
        return v


class PengujiDraft(BaseModel):
    nama: Optional[str] = None
    pendidikan_terakhir: Optional[str] = None
    asal_sekolah: Optional[str] = None
    mata_pelajaran: Optional[str] = None

class SaveDraftRequest(BaseModel):
    penguji: PengujiDraft
    judul_soal: Optional[str] = None
    soal_snapshot: Optional[List[Dict[str, Any]]] = None
    eval_draft: Optional[Dict[str, Any]] = None
    last_step: Optional[int] = 1
    id_penguji: Optional[int] = None


class UpdateRekapRequest(BaseModel):
    evaluasi_list: List[EvaluasiItem]


# ================================================================
# HELPER
# ================================================================

def _hitung_dan_simpan_evaluasi(db, penguji_obj, evaluasi_list):
    db.query(EvaluasiSoal).filter(EvaluasiSoal.id_penguji == penguji_obj.id).delete()

    total_skor_semua = 0
    jumlah_soal = len(evaluasi_list)

    for item in evaluasi_list:
        if item.id_soal and item.id_soal > 0:
            soal = db.query(Soal).filter(Soal.id == item.id_soal).first()
            if not soal:
                db.rollback()
                raise HTTPException(status_code=404, detail=f"Soal id {item.id_soal} tidak ditemukan")

        skor_soal = (
            item.kesesuaian_soal
            + item.kebenaran_jawaban
            + item.kebenaran_pembahasan
            + item.kesesuaian_level_kognitif
            + item.konstruksi_soal
        )
        total_skor_semua += skor_soal

        id_soal_final = item.id_soal if item.id_soal and item.id_soal > 0 else None

        evaluasi = EvaluasiSoal(
            id_penguji=penguji_obj.id,
            id_soal=id_soal_final,
            kode_soal=item.kode_soal,
            kesesuaian_soal=item.kesesuaian_soal,
            kebenaran_jawaban=item.kebenaran_jawaban,
            kebenaran_pembahasan=item.kebenaran_pembahasan,
            kesesuaian_level_kognitif=item.kesesuaian_level_kognitif,
            konstruksi_soal=item.konstruksi_soal,
            level_kognitif_sistem=item.level_kognitif_sistem,
            level_kognitif_evaluator=item.level_kognitif_evaluator,
            total_skor=skor_soal,
            catatan=item.catatan,
        )
        db.add(evaluasi)

    skor_maksimal = jumlah_soal * SKOR_MAKS_PER_SOAL
    nilai_akhir = round((total_skor_semua / skor_maksimal) * 100, 2) if skor_maksimal > 0 else 0
    penguji_obj.nilai_akhir = nilai_akhir

    return total_skor_semua, skor_maksimal, nilai_akhir, jumlah_soal


# ================================================================
# ENDPOINT
# ================================================================

@router.post("/submit")
def submit_evaluasi(request: SubmitEvaluasiRequest, db: Session = Depends(get_db)):
    penguji = PengujianPenguji(
        nama=request.penguji.nama,
        pendidikan_terakhir=request.penguji.pendidikan_terakhir,
        asal_sekolah=request.penguji.asal_sekolah,
        mata_pelajaran=request.penguji.mata_pelajaran,
        judul_soal=request.judul_soal,
        soal_snapshot=request.soal_snapshot,
        status="selesai",
        last_step=2,
        eval_draft=None,
    )
    db.add(penguji)
    db.flush()

    total, maks, nilai, jumlah = _hitung_dan_simpan_evaluasi(db, penguji, request.evaluasi_list)

    db.commit()
    db.refresh(penguji)

    return {
        "status": "success",
        "id_penguji": penguji.id,
        "nama_penguji": penguji.nama,
        "jumlah_soal_dievaluasi": jumlah,
        "total_skor_diperoleh": total,
        "skor_maksimal": maks,
        "nilai_akhir_persen": nilai,
    }


@router.post("/draft")
def save_draft(request: SaveDraftRequest, db: Session = Depends(get_db)):
    if request.id_penguji:
        penguji = db.query(PengujianPenguji).filter(PengujianPenguji.id == request.id_penguji).first()
        if not penguji:
            raise HTTPException(status_code=404, detail="Draft tidak ditemukan")
    else:
        penguji = PengujianPenguji(status="draft")
        db.add(penguji)
        db.flush()

    penguji.nama = request.penguji.nama
    penguji.pendidikan_terakhir = request.penguji.pendidikan_terakhir
    penguji.asal_sekolah = request.penguji.asal_sekolah
    penguji.mata_pelajaran = request.penguji.mata_pelajaran
    penguji.judul_soal = request.judul_soal
    penguji.soal_snapshot = request.soal_snapshot
    penguji.eval_draft = request.eval_draft
    penguji.last_step = request.last_step or 1
    penguji.status = "draft"

    db.commit()
    db.refresh(penguji)

    return {
        "status": "draft_saved",
        "id_penguji": penguji.id,
        "message": "Progres pengujian berhasil disimpan.",
    }


@router.put("/update/{id_penguji}")
def update_rekap(id_penguji: int, request: UpdateRekapRequest, db: Session = Depends(get_db)):
    penguji = db.query(PengujianPenguji).filter(PengujianPenguji.id == id_penguji).first()
    if not penguji:
        raise HTTPException(status_code=404, detail="Data penguji tidak ditemukan")

    total, maks, nilai, jumlah = _hitung_dan_simpan_evaluasi(db, penguji, request.evaluasi_list)
    penguji.status = "selesai"

    db.commit()
    db.refresh(penguji)

    return {
        "status": "updated",
        "id_penguji": penguji.id,
        "jumlah_soal_dievaluasi": jumlah,
        "total_skor_diperoleh": total,
        "skor_maksimal": maks,
        "nilai_akhir_persen": nilai,
    }


@router.delete("/hapus/{id_penguji}")
def hapus_pengujian(id_penguji: int, db: Session = Depends(get_db)):
    penguji = db.query(PengujianPenguji).filter(PengujianPenguji.id == id_penguji).first()
    if not penguji:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan")
    db.delete(penguji)
    db.commit()
    return {"status": "deleted", "id_penguji": id_penguji}


@router.get("/rekap/{id_penguji}")
def get_rekap_penguji(id_penguji: int, db: Session = Depends(get_db)):
    penguji = db.query(PengujianPenguji).filter(PengujianPenguji.id == id_penguji).first()
    if not penguji:
        raise HTTPException(status_code=404, detail="Penguji tidak ditemukan")

    evaluasi_list = db.query(EvaluasiSoal).filter(EvaluasiSoal.id_penguji == id_penguji).all()

    return {
        "penguji": {
            "id": penguji.id,
            "nama": penguji.nama,
            "pendidikan_terakhir": penguji.pendidikan_terakhir,
            "asal_sekolah": penguji.asal_sekolah,
            "mata_pelajaran": penguji.mata_pelajaran,
            "judul_soal": penguji.judul_soal,
            "nilai_akhir_persen": penguji.nilai_akhir,
            "status": penguji.status,
            "soal_snapshot": penguji.soal_snapshot,
            "eval_draft": penguji.eval_draft,
            "last_step": penguji.last_step,
            "created_at": str(penguji.created_at) if penguji.created_at else None,
            "updated_at": str(penguji.updated_at) if penguji.updated_at else None,
        },
        "evaluasi": [
            {
                "kode_soal": e.kode_soal,
                "kesesuaian_soal": e.kesesuaian_soal,
                "kebenaran_jawaban": e.kebenaran_jawaban,
                "kebenaran_pembahasan": e.kebenaran_pembahasan,
                "level_kognitif_sistem": e.level_kognitif_sistem,
                "level_kognitif_evaluator": e.level_kognitif_evaluator,
                "kesesuaian_level_kognitif": e.kesesuaian_level_kognitif,
                "konstruksi_soal": e.konstruksi_soal,
                "total_skor": e.total_skor,
                "catatan": e.catatan,
            }
            for e in evaluasi_list
        ],
    }


@router.get("/riwayat")
def get_riwayat(db: Session = Depends(get_db)):
    penguji_list = db.query(PengujianPenguji).order_by(PengujianPenguji.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "nama": p.nama,
            "pendidikan_terakhir": p.pendidikan_terakhir,
            "asal_sekolah": p.asal_sekolah,
            "mata_pelajaran": p.mata_pelajaran,
            "judul_soal": p.judul_soal,
            "nilai_akhir_persen": p.nilai_akhir,
            "status": p.status,
            "last_step": p.last_step,
            "soal_snapshot": p.soal_snapshot,
            "eval_draft": p.eval_draft,
            "created_at": str(p.created_at) if p.created_at else None,
            "updated_at": str(p.updated_at) if p.updated_at else None,
        }
        for p in penguji_list
    ]