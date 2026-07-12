import logging
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None):
        self.model = SentenceTransformer(model_name or settings.embedding_model)

    def encode(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()


class RAGRetriever:
    def __init__(self, vector_store, embedder: Embedder):
        self.vs = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, role: str, k: int | None = None, collection_name: str | None = None) -> list:
        query_embedding = self.embedder.encode(query)
        k = k or settings.retrieval_k
        col = collection_name or f"kb_{role}"
        chunks = self.vs.query(
            collection=col,
            query_embedding=query_embedding,
            k=k,
        )
        threshold = settings.similarity_threshold
        filtered = [c for c in chunks if c.score >= threshold]
        if not filtered:
            logger.warning("All %d chunks below threshold %s for query: %s", len(chunks), threshold, query[:80])
        return filtered
