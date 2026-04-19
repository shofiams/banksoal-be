from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Modul(Base):
    __tablename__ = "modul"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(255), nullable=False)
    deskripsi = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
