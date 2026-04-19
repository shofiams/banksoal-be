from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Topik(Base):
    __tablename__ = "topik"

    id = Column(Integer, primary_key=True, index=True)
    id_jenjang = Column(Integer, ForeignKey("jenjang.id"), nullable=False)
    id_modul = Column(Integer, ForeignKey("modul.id"), nullable=False)

    nama = Column(String(255), nullable=False)
    deskripsi = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
