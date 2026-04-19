from datetime import datetime
from app.core.database import SessionLocal
from app.models.soal import Soal
from app.models.opsi_soal import OpsiSoal


def save_generated_soal(
    generated_list,
    id_topik,
    tipe_generate
):
    db = SessionLocal()

    try:
        for item in generated_list:

            # 🔥 fleksibel: ambil key yang tersedia
            pertanyaan = item.get("text_soal") or item.get("soal")
            pembahasan = item.get("pembahasan")
            level = item.get("tingkat_kognitif") or item.get("level")

            new_soal = Soal(
                id_topik=id_topik,
                pertanyaan=pertanyaan,
                pembahasan=pembahasan,
                tipe=tipe_generate,
                level_kognitif=level,
                created_at=datetime.utcnow()
            )

            db.add(new_soal)
            db.flush()

            # 🔥 handle struktur pilihan berbeda
            pilihan_list = item.get("pilihan") or item.get("opsi")

            if pilihan_list:
                for opsi in pilihan_list:

                    # extract format
                    teks_raw = opsi.get("text") or opsi.get("teks") or ""
                    benar = opsi.get("is_correct")

                    # jika format extract pakai "jawaban"
                    if benar is None and item.get("jawaban"):
                        benar = teks_raw == item.get("jawaban")

                    # --- ambil label (A/B/C/D/E) ---
                    label = opsi.get("label")

                    # Jika label tidak ada, coba deteksi dari teks: "A. ..." atau "A) ..."
                    if not label:
                        import re
                        m = re.match(r'^([A-Ea-e])[.)]\s*', teks_raw)
                        if m:
                            label = m.group(1).upper()

                    # Jika masih tidak ada, generate berdasarkan urutan (A, B, C, D, E)
                    if not label:
                        idx = pilihan_list.index(opsi)
                        label = chr(65 + idx)  # 65 = ord('A')

                    # Bersihkan teks dari prefix label jika ada ("A. teks" -> "teks")
                    import re as _re
                    teks = _re.sub(r'^[A-Ea-e][.)]\s*', '', teks_raw).strip() or teks_raw

                    new_opsi = OpsiSoal(
                        id_soal=new_soal.id,
                        label=label,
                        teks=teks,
                        kunci_jawaban=bool(benar)
                    )

                    db.add(new_opsi)

        db.commit()
        print("Soal berhasil disimpan.")

    except Exception as e:
        db.rollback()
        print("ERROR SAVE:", e)
        raise

    finally:
        db.close()