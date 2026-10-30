"""Embedding models served by the gateway's OpenAI-style /v1/embeddings endpoint.

One embedding model is shared by every method in a run, so retrieval quality differences come
from the methods, not from different embedders.
"""

import hashlib
import math
import re

import numpy as np


class HashEmbedder:
    """Deterministic hashed bag-of-words vectors. For offline tests only: no download, but
    texts that share words still get similar vectors."""

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.name = f"hash:{dim}"

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"\w+", text.lower()):
                digest = hashlib.md5(word.encode()).digest()
                index = int.from_bytes(digest[:4], "little") % self.dim
                out[row, index] += 1.0 if digest[4] % 2 else -1.0
            norm = math.sqrt(float((out[row] ** 2).sum()))
            if norm:
                out[row] /= norm
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.name = model_name
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                 convert_to_numpy=True).astype(np.float32)


def load_embedder(spec: str):
    """`hash:<dim>` for the offline test embedder, otherwise a sentence-transformers model id."""
    if spec.startswith("hash:"):
        return HashEmbedder(int(spec.split(":", 1)[1]))
    return SentenceTransformerEmbedder(spec)
