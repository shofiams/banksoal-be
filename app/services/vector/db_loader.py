from sqlalchemy.orm import joinedload
from app.models.soal import Soal
from app.core.database import SessionLocal

# tahap 4a recreate
def get_soal_lama(id_topik, level_list):
    """
    Mengambil soal lama dari database berdasarkan topik dan level.
    """

    # get soal lama utama
    db = SessionLocal()
    try:
        soal_list = (
            db.query(Soal)
            .options(joinedload(Soal.opsi))
            .filter(
                Soal.id_topik == id_topik,
                Soal.level_kognitif.in_(level_list)
            )
            .all()
        )
        return soal_list
    finally:
        db.close()