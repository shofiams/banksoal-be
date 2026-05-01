from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Database
from app.core.database import Base, engine

# Import semua model agar ter-register di metadata
from app.models import *

# API Router v1
from app.api.v1.router import api_router


# BUAT APP DULU
app = FastAPI(
    title="BANKSOAL_BE API",
    version="1.0.0",
    description="Backend API untuk sistem Bank Soal berbasis AI (Extract & Recreate)"
)

# BUAT SEMUA TABEL JIKA BELUM ADA
Base.metadata.create_all(bind=engine)

# TAMBAHKAN CORS — izinkan semua origin lokal yang mungkin dipakai Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# menghubungkan semua route ke aplikasi (utama)
app.include_router(api_router, prefix="/api/v1")