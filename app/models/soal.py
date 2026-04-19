from sqlalchemy import Column, Integer, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.opsi_soal import OpsiSoal
from app.core.database import Base
import enum

class TipeSoal(enum.Enum):
    pilihan_ganda = "pilihan_ganda"
    extract = "extract"
    recreate = "recreate"

class LevelKognitif(enum.Enum):
    LOTS = "LOTS"
    MOTS = "MOTS"
    HOTS = "HOTS"

class Soal(Base):
    __tablename__ = "soal"

    id = Column(Integer, primary_key=True, index=True)
    id_topik = Column(Integer, ForeignKey("topik.id"), nullable=False)

    pertanyaan = Column(Text, nullable=False)
    pembahasan = Column(Text)

    tipe = Column(Enum(TipeSoal), nullable=False)
    level_kognitif = Column(Enum(LevelKognitif), nullable=False)

    # FIX: tambah cascade="all, delete-orphan" agar opsi ikut terhapus saat soal dihapus
    opsi = relationship("OpsiSoal", backref="soal", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())