import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.rag.vector_store import Chunk
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.vector_store_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def upsert(self, collection: str, ids: list[str], embeddings: list[list[float]],
               metadatas: list[dict], documents: list[str]) -> None:
        col = self.client.get_or_create_collection(collection)
        col.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        logger.debug("Upserted %d items to collection '%s'", len(ids), collection)

    def query(self, collection: str, query_embedding: list[float],
              k: int, filter: dict | None = None) -> list[Chunk]:
        try:
            col = self.client.get_collection(collection)
        except ValueError:
            logger.warning("Collection '%s' not found", collection)
            return []

        results = col.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter,
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                chunks.append(Chunk(
                    id=results["ids"][0][i],
                    text=results["documents"][0][i],
                    score=results["distances"][0][i] if results.get("distances") else 0.0,
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                ))
        return chunks
