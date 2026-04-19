from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import requests
import os

print("LOADED INDOBERT FILE")

# ============================================================
# GANTI URL INI setiap kali buka Colab baru
# =============================
COLAB_EMBED_URL = "https://tutorials-composer-builds-footage.trycloudflare.com"  # contoh: "https://xxxx.ngrok-free.dev"

# Header wajib untuk bypass halaman warning ngrok gratis
NGROK_HEADERS = {
    "ngrok-skip-browser-warning": "true",
    "Content-Type": "application/json"
}


def _use_colab() -> bool:
    """Cek apakah Colab embedding server tersedia."""
    if not COLAB_EMBED_URL:
        return False
    try:
        r = requests.get(
            f"{COLAB_EMBED_URL}/health",
            headers=NGROK_HEADERS,
            timeout=3
        )
        # Pastikan response JSON bukan HTML ngrok
        data = r.json()
        return data.get("status") == "ok"
    except Exception:
        return False


# ── Load model lokal (fallback) ──
MODEL_NAME = "indobenchmark/indobert-base-p1"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()

print(f"Local model loaded di: {device}")
if COLAB_EMBED_URL:
    if _use_colab():
        print(f"✅ Colab GPU tersedia → embedding akan pakai Colab")
    else:
        print(f"⚠️  Colab URL diset tapi tidak bisa diakses → fallback ke {device}")
else:
    print(f"ℹ️  Colab tidak diset → pakai {device} lokal")


class IndoBERTEmbedder:

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_batch([text], batch_size=1)[0]

    def embed_batch(self, texts: list, batch_size: int = 32) -> np.ndarray:

        # ── Coba pakai Colab GPU ──
        if _use_colab():
            try:
                r = requests.post(
                    f"{COLAB_EMBED_URL}/embed",
                    json={"texts": texts, "batch_size": batch_size},
                    headers=NGROK_HEADERS,
                    timeout=120
                )
                if r.status_code == 200:
                    data = r.json()
                    # Pastikan response adalah JSON embedding, bukan HTML
                    if "embeddings" in data:
                        print(f"✅ Embedding {len(texts)} teks via Colab GPU")
                        return np.array(data["embeddings"])
            except Exception as e:
                print(f"⚠️  Colab gagal ({e}) → fallback ke lokal")

        # ── Fallback lokal ──
        print(f"ℹ️  Embedding {len(texts)} teks di {device} (lokal)...")
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            inputs = tokenizer(
                batch_texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model(**inputs)

            emb = outputs.last_hidden_state.mean(dim=1)
            all_embeddings.extend(emb.cpu().numpy())

        return np.array(all_embeddings)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_text(text)

    def embed_text_debug(self, text: str) -> np.ndarray:
        using_colab = _use_colab()
        print(f"\n[DEBUG] Mode: {'Colab GPU' if using_colab else f'Lokal {device}'}")
        print(f"[DEBUG] Input: {text[:80]}...")
        result = self.embed_text(text)
        print(f"[DEBUG] Shape: {result.shape}")
        return result


# ── Backward compatibility ──
_embedder_instance = IndoBERTEmbedder()

def embed_text(text: str) -> np.ndarray:
    return _embedder_instance.embed_text(text)

def embed_text_debug(text: str) -> np.ndarray:
    return _embedder_instance.embed_text_debug(text)