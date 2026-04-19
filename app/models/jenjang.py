from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Jenjang(Base):
    __tablename__ = "jenjang"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100), nullable=False)
    alias = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
