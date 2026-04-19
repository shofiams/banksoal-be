from fastapi import APIRouter

# v1 routes
from app.api.v1.master_routes import router as master_router
from app.api.recreate_routes import router as recreate_router
from app.api.extract_routes import router as extract_router
from app.api import soal_routes
# PENGUJIAN — hapus baris ini saat penyerahan ke mitra
from app.api.v1.pengujian_routes import router as pengujian_router

api_router = APIRouter()

# ======================
# MASTER DATA
# ======================
api_router.include_router(master_router)

# ======================
# AI FEATURES
# ======================
api_router.include_router(
    recreate_router,
    prefix="/ai",
    tags=["AI Recreate"]
)

api_router.include_router(
    extract_router,
    prefix="/ai",
    tags=["AI Extract"]
)

# ======================
# SOAL MANAGEMENT
# ======================
api_router.include_router(soal_routes.router)

# ======================
# PENGUJIAN — hapus saat penyerahan ke mitra
# ======================
api_router.include_router(pengujian_router)