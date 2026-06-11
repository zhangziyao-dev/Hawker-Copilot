import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Tuple
import logging

from backend.intelligence.embedder import embed_texts, embed_single, build_scenario_narrative
from backend.intelligence.schemas import DemandScenario

logger = logging.getLogger(__name__)

VECTOR_STORE_PATH = "models/vector_store.pkl"


class DemandVectorStore:
    """
    FAISS-backed vector store for historical demand scenarios.
    Supports build, persist, load, and similarity search.
    """

    def __init__(self):
        self.index = None          # FAISS index
        self.scenarios: List[DemandScenario] = []
        self.narratives: List[str] = []
        self.dimension = 384       # all-MiniLM-L6-v2 output size

    def build(self, scenarios: List[DemandScenario]):
        """Build FAISS index from list of DemandScenario objects."""
        logger.info(f"Building vector store with {len(scenarios)} scenarios...")

        self.scenarios = scenarios
        self.narratives = [s.narrative for s in scenarios]

        # Embed all narratives
        embeddings = embed_texts(self.narratives)

        # Inner product index (cosine sim since embeddings are normalized)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)

        logger.info(f"Vector store built. Total vectors: {self.index.ntotal}")

    def search(self, query_text: str, top_k: int = 5) -> List[Tuple[DemandScenario, float]]:
        """
        Search for most similar historical scenarios.
        Returns list of (scenario, similarity_score) tuples.
        """
        if self.index is None:
            raise RuntimeError("Vector store not built. Call build() first.")

        query_embedding = embed_single(query_text)
        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # FAISS returns -1 for empty slots
                results.append((self.scenarios[idx], float(score)))

        return results

    def save(self, path: str = VECTOR_STORE_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Vector store saved to {path}")

    @classmethod
    def load(cls, path: str = VECTOR_STORE_PATH) -> "DemandVectorStore":
        with open(path, "rb") as f:
            store = pickle.load(f)
        logger.info(f"Vector store loaded. Vectors: {store.index.ntotal}")
        return store