from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import requests
import traceback

print("LOADED INDOBERT FILE")

HF_EMBED_URL = "https://shofiams40-indobert-embedding-api.hf.space"
HF_HEADERS = {"Content-Type": "application/json"}


def _use_hf() -> bool:
    if not HF_EMBED_URL:
        return False
    try:
        r = requests.get(f"{HF_EMBED_URL}/health", headers=HF_HEADERS, timeout=30)
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
if _use_hf():
    print(f"✅ HF Spaces tersedia → embedding akan pakai HF Spaces")
else:
    print(f"⚠️  HF tidak bisa diakses → fallback ke {device}")


class IndoBERTEmbedder:

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_batch([text], batch_size=1)[0]

    # proses utama embed
    def embed_batch(self, texts: list, batch_size: int = 32) -> np.ndarray:
        hf_aktif = _use_hf()
        print(f"[DEBUG] HF aktif: {hf_aktif}")

        if hf_aktif:
            try:
                r = requests.post(
                    f"{HF_EMBED_URL}/embed",
                    json={"texts": texts, "batch_size": batch_size},
                    headers=HF_HEADERS,
                    timeout=120
                )
                print(f"[DEBUG] Status code: {r.status_code}")
                print(f"[DEBUG] Response: {r.text[:200]}")
                if r.status_code == 200:
                    data = r.json()
                    if "embeddings" in data:
                        print(f"✅ Embedding {len(texts)} teks via HF Spaces")
                        return np.array(data["embeddings"])
            except Exception as e:
                print(f"⚠️  HF Spaces gagal → fallback ke lokal")
                print(f"[ERROR DETAIL] {type(e).__name__}: {e}")
                traceback.print_exc()

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
        using_hf = _use_hf()
        print(f"\n[DEBUG] Mode: {'HF Spaces' if using_hf else f'Lokal {device}'}")
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