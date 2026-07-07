import logging
from app.rag.retriever import RAGRetriever
from app.rag.vector_store import Chunk

logger = logging.getLogger(__name__)


class RAGPipelineService:
    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever

    def retrieve_for_queries(self, queries: list[str], role: str) -> dict[str, list[Chunk]]:
        results: dict[str, list[Chunk]] = {}
        for query in queries:
            chunks = self.retriever.retrieve(query, role)
            results[query] = chunks
            logger.debug("Query '%s...' returned %d chunks", query[:60], len(chunks))
        return results
