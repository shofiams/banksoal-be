from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, validator
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models.soal import Soal
from app.models.opsi_soal import OpsiSoal
from app.services.persistence.save_soal_service import save_generated_soal


router = APIRouter(prefix="/soal", tags=["Soal Management"])


# DATABASE DEPENDENCY

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# REQUEST SCHEMA

class OpsiItem(BaseModel):
    text: str
    is_correct: bool


class SoalItem(BaseModel):
    text_soal: str
    pembahasan: str
    tingkat_kognitif: str
    pilihan: List[OpsiItem]

    @validator("tingkat_kognitif")
    def validate_level(cls, v):
        allowed = {"LOTS", "MOTS", "HOTS"}
        if v.upper() not in allowed:
            raise ValueError(f"tingkat_kognitif harus salah satu dari: {allowed}")
        return v.upper()

    @validator("pilihan")
    def validate_pilihan(cls, v):
        if len(v) < 2:
            raise ValueError("Setiap soal harus memiliki minimal 2 pilihan jawaban")

        benar = [o for o in v if o.is_correct]
        if len(benar) != 1:
            raise ValueError("Setiap soal harus memiliki tepat 1 jawaban benar")

        return v


class SaveSoalRequest(BaseModel):
    id_topik: int
    tipe: str  # "extract" atau "recreate"
    soal_list: List[SoalItem]

    @validator("tipe")
    def validate_tipe(cls, v):
        allowed = {"extract", "recreate", "pilihan_ganda"}
        if v not in allowed:
            raise ValueError(f"tipe harus salah satu dari: {allowed}")
        return v

    @validator("soal_list")
    def validate_soal_not_empty(cls, v):
        if not v:
            raise ValueError("soal_list tidak boleh kosong")
        return v


# SAVE ENDPOINT
# utama penyimpanan utama
@router.post("/save")
def save_soal(request: SaveSoalRequest):
    try:
        save_generated_soal(
            generated_list=[item.dict() for item in request.soal_list],
            id_topik=request.id_topik,
            tipe_generate=request.tipe
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menyimpan soal: {str(e)}"
        )

    return {
        "status": "success",
        "message": f"Berhasil menyimpan {len(request.soal_list)} soal ke database",
        "id_topik": request.id_topik,
        "tipe": request.tipe,
        "jumlah_tersimpan": len(request.soal_list)
    }


# ==============================
# GET LIST SOAL (UNTUK FRONTEND)
# ==============================

@router.get("/")
def list_soal(
    topik_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Soal).options(joinedload(Soal.opsi))

    if topik_id:
        query = query.filter(Soal.id_topik == topik_id)

    soal_list = query.all()

    # Return eksplisit agar relasi opsi ikut ter-serialize
    return [
        {
            "id":             s.id,
            "id_topik":       s.id_topik,
            "pertanyaan":     s.pertanyaan,
            "pembahasan":     s.pembahasan,
            "tipe":           s.tipe.value if s.tipe else None,
            "level_kognitif": s.level_kognitif.value if s.level_kognitif else None,
            "opsi": [
                {
                    "id":            o.id,
                    "label":         o.label,
                    "teks":          o.teks,
                    "kunci_jawaban": o.kunci_jawaban,
                }
                for o in sorted(s.opsi, key=lambda x: x.label or "")
            ],
        }
        for s in soal_list
    ]


# ==============================
# DELETE SOAL


@router.delete("/{soal_id}")
def delete_soal(soal_id: int, db: Session = Depends(get_db)):
    soal = db.query(Soal).filter(Soal.id == soal_id).first()

    if not soal:
        raise HTTPException(status_code=404, detail="Soal tidak ditemukan")

    db.delete(soal)
    db.commit()

    return {"message": "Soal berhasil dihapus"}