"""
Model untuk fitur PENGUJIAN KUALITAS SOAL (kebutuhan akademik/dosen).
Catatan: Tabel ini HANYA untuk keperluan pengujian/validasi penelitian.
Saat penyerahan ke mitra, hapus:
  - File ini (models/pengujian.py)
  - app/api/v1/pengujian_routes.py
  - Import di app/models/__init__.py (baris pengujian)
  - Import di app/api/v1/router.py (baris pengujian)
  - Frontend: src/features/pengujian/ (seluruh folder)
  - Route di AppRouter.jsx (baris /pengujian)
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PengujianPenguji(Base):
    """
    Biodata guru penguji yang melakukan evaluasi kualitas soal.
    """
    __tablename__ = "pengujian_penguji"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(150), nullable=True)
    pendidikan_terakhir = Column(String(100), nullable=True)
    asal_sekolah = Column(String(255), nullable=True)
    mata_pelajaran = Column(String(150), nullable=True)

    # Judul output soal yang diuji
    judul_soal = Column(String(500), nullable=True)

    # Nilai akhir diisi otomatis dari rekapan EvaluasiSoal
    nilai_akhir = Column(Float, nullable=True)

    # Status: 'draft' = belum selesai, 'selesai' = sudah submit final
    status = Column(String(20), nullable=False, default="draft")

    # Snapshot data soal (untuk resume pengujian)
    soal_snapshot = Column(JSON, nullable=True)

    # Snapshot evalData sementara (untuk resume draft)
    eval_draft = Column(JSON, nullable=True)

    # Step terakhir (0=biodata, 1=evaluasi, 2=hasil)
    last_step = Column(Integer, nullable=False, default=0)

    created_at = Column(Date, server_default=func.current_date())
    updated_at = Column(Date, onupdate=func.current_date())

    evaluasi = relationship("EvaluasiSoal", back_populates="penguji", cascade="all, delete-orphan")


class EvaluasiSoal(Base):
    """
    Evaluasi per soal oleh penguji.
    Setiap baris mewakili satu soal yang dinilai oleh satu penguji.

    Aspek penilaian sesuai tabel pengujian:
      - kesesuaian_soal     : 1-4
      - kebenaran_jawaban   : 1-4
      - kebenaran_pembahasan: 1-4
      - level_kognitif_sistem: LOTS/MOTS/HOTS (dari sistem)
      - level_kognitif_evaluator: LOTS/MOTS/HOTS (menurut penguji)
      - kesesuaian_level_kognitif: 1-4
      - konstruksi_soal     : 1-4

    Total skor per soal = jumlah 5 nilai numerik (maks 20).
    Kualitas (%) = (Total seluruh skor) / (jumlah_soal × 5_aspek × 4_maks) × 100%
    """
    __tablename__ = "evaluasi_soal"

    id = Column(Integer, primary_key=True, index=True)
    id_penguji = Column(Integer, ForeignKey("pengujian_penguji.id"), nullable=False)
    # nullable=True agar soal yang belum disimpan ke DB tetap bisa dievaluasi
    id_soal = Column(Integer, ForeignKey("soal.id"), nullable=True)

    kode_soal = Column(String(20), nullable=False)  # e.g. "D1", "D2", ...

    # Aspek numerik (skala 1-4)
    kesesuaian_soal = Column(Integer, nullable=False)           # 1-4
    kebenaran_jawaban = Column(Integer, nullable=False)         # 1-4
    kebenaran_pembahasan = Column(Integer, nullable=False)      # 1-4
    kesesuaian_level_kognitif = Column(Integer, nullable=False) # 1-4
    konstruksi_soal = Column(Integer, nullable=False)           # 1-4

    # Aspek kategori
    level_kognitif_sistem = Column(String(10), nullable=False)      # dari sistem (LOTS/MOTS/HOTS)
    level_kognitif_evaluator = Column(String(10), nullable=False)   # menurut penguji

    # Skor total per soal (dihitung otomatis: 5 aspek numerik dijumlah, maks 20)
    total_skor = Column(Integer, nullable=True)

    catatan = Column(Text, nullable=True)

    created_at = Column(Date, server_default=func.current_date())
    updated_at = Column(Date, onupdate=func.current_date())

    penguji = relationship("PengujianPenguji", back_populates="evaluasi")