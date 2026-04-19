from app.core.database import SessionLocal
from app.models.topik import Topik

def validate_topik_recreate(topik_nama: str):
    db = SessionLocal()
    try:
        topik = db.query(Topik).filter(Topik.nama == topik_nama).first()
        if not topik:
            raise ValueError(
                "Topik tidak ditemukan di database. AI Recreate hanya menerima topik yang sudah ada."
            )
        return topik
    finally:
        db.close()
