from app.core.database import SessionLocal
from app.models.soal import Soal

db = SessionLocal()

try:
    total = db.query(Soal).count()
    print(f"✅ Query berhasil, jumlah soal: {total}")
except Exception as e:
    print("❌ Query gagal")
    print(e)
finally:
    db.close()
