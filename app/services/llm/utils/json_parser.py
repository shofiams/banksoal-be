import json
import re


def clean_and_parse_json(text: str):
    """
    Parser JSON toleran.
    Tidak mudah gagal.
    """

    if not text:
        return []

    # 1️⃣ Hapus markdown block
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    text = text.strip()

    # 2️⃣ Ambil hanya bagian array JSON
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1:
        text = text[start:end+1]

    # 3️⃣ Coba parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 4️⃣ Coba perbaiki trailing comma
    try:
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        return json.loads(text)
    except Exception:
        return []
