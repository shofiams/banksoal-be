from app.core.database import engine

try:
    with engine.connect() as conn:
        print("✅ Database TERHUBUNG")
except Exception as e:
    print("❌ Database TIDAK TERHUBUNG")
    print(e)
