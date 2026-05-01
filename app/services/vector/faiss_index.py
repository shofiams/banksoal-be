import faiss
import numpy as np


class FaissIndex:
    def __init__(self, dimension: int = 768, metric: str = "l2"):
        """
        metric:
            - "l2" (default)  -> Euclidean (untuk AI Recreate)
            - "cosine"        -> Cosine similarity (untuk AI Extract)
        """
        self.dimension = dimension
        self.metric = metric.lower()

        # proses utama saat inialisai
        if self.metric == "cosine":
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.index = faiss.IndexFlatL2(dimension)

        self.metadata = []

    def _normalize(self, vectors: np.ndarray):
        if self.metric == "cosine":
            faiss.normalize_L2(vectors)

    #  utama saat simpan
    def add_vector(self, vector: np.ndarray, meta: dict):
        vector = np.array([vector]).astype("float32")
        self._normalize(vector)
        self.index.add(vector)
        self.metadata.append(meta)

    #  utama saat pencarian disini proses semantic search
    def search(self, query_vector: np.ndarray, k: int = 5):
        query_vector = np.array([query_vector]).astype("float32")
        self._normalize(query_vector)

        distances, indices = self.index.search(query_vector, k)

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                item = self.metadata[idx].copy()
                item["score"] = float(score)
                results.append(item)

        return results

