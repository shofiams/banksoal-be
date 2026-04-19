from app.services.recreate.recreate_pipeline import run_recreate_pipeline

distribusi = {
    "LOTS": 1,
    "MOTS": 1
}

hasil = run_recreate_pipeline(
    id_topik=1,
    jenjang="SMA",
    modul="Biologi",
    nama_topik="Sistem Pernapasan",
    jumlah_soal=2,
    distribusi_level=distribusi
)

print("HASIL LLM:")
print(hasil)
