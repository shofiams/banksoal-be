from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import SessionLocal
from app.models.jenjang import Jenjang
from app.models.modul import Modul
from app.models.topik import Topik

router = APIRouter(prefix="/master", tags=["Master"])


# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# JENJANG
@router.get("/jenjang") 
def list_jenjang(db: Session = Depends(get_db)):
    return db.query(Jenjang).all()


class CreateJenjangRequest(BaseModel):
    nama: str
    alias: Optional[str] = None


@router.post("/jenjang")
def create_jenjang(request: CreateJenjangRequest, db: Session = Depends(get_db)):
    """Buat jenjang baru jika belum ada (case-insensitive)."""
    existing = db.query(Jenjang).filter(Jenjang.nama.ilike(request.nama.strip())).first()
    if existing:
        return {"status": "exists", "id": existing.id, "nama": existing.nama}
    jenjang = Jenjang(nama=request.nama.strip(), alias=request.alias)
    db.add(jenjang)
    db.commit()
    db.refresh(jenjang)
    return {"status": "created", "id": jenjang.id, "nama": jenjang.nama}


# MODUL
@router.get("/modul")
def list_modul(db: Session = Depends(get_db)):
    return db.query(Modul).all()


# TOPIK

@router.get("/topik")
def list_topik(
    jenjang_id: Optional[int] = Query(None),
    modul_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Topik)

    if jenjang_id:
        query = query.filter(Topik.id_jenjang == jenjang_id)

    if modul_id:
        query = query.filter(Topik.id_modul == modul_id)

    return query.all()


# CREATE MODUL + TOPIK BARU

class CreateTopikRequest(BaseModel):
    nama_modul: str
    nama_topik: str
    id_jenjang: Optional[int] = None   # bisa None jika jenjang baru
    nama_jenjang: Optional[str] = None  # diisi jika jenjang baru (belum ada id)


@router.post("/create-topik")
def create_modul_topik_baru(
    request: CreateTopikRequest,
    db: Session = Depends(get_db)
):
    """
    Auto-create jenjang (jika baru) + modul + topik baru jika belum ada di database.
    Dipakai saat Extract dengan inputan manual (modul/topik/jenjang baru).
    """

    # 0. Resolve id_jenjang — buat baru jika belum ada
    id_jenjang = request.id_jenjang
    if not id_jenjang:
        nama_jenjang = (request.nama_jenjang or "").strip()
        if not nama_jenjang:
            raise HTTPException(status_code=400, detail="nama_jenjang wajib diisi jika id_jenjang tidak diberikan")
        
        jenjang = db.query(Jenjang).filter(
            Jenjang.nama.ilike(nama_jenjang)
        ).first()

        if not jenjang:
            jenjang = Jenjang(nama=nama_jenjang)
            db.add(jenjang)
            db.flush()

        id_jenjang = jenjang.id

    # 1. Cek apakah modul sudah ada (case-insensitive)
    modul = db.query(Modul).filter(
        Modul.nama.ilike(request.nama_modul.strip())
    ).first()

    if not modul:
        modul = Modul(nama=request.nama_modul.strip())
        db.add(modul)
        db.flush()

    # 2. Cek apakah topik sudah ada di modul + jenjang ini
    topik = db.query(Topik).filter(
        Topik.id_modul == modul.id,
        Topik.id_jenjang == id_jenjang,
        Topik.nama.ilike(request.nama_topik.strip())
    ).first()

    if not topik:
        topik = Topik(
            nama=request.nama_topik.strip(),
            id_modul=modul.id,
            id_jenjang=id_jenjang,
        )
        db.add(topik)

    db.commit()
    db.refresh(topik)

    return {
        "status": "success",
        "id_jenjang": id_jenjang,
        "id_modul": modul.id,
        "nama_modul": modul.nama,
        "id_topik": topik.id,
        "nama_topik": topik.nama,
    }