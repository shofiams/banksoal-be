from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.core.database import Base

class OpsiSoal(Base):
    __tablename__ = "opsi_soal"

    id = Column(Integer, primary_key=True, index=True)
    id_soal = Column(Integer, ForeignKey("soal.id"), nullable=False)

    label = Column(String(10))
    teks = Column(String(255), nullable=False)
    kunci_jawaban = Column(Boolean, default=False)
