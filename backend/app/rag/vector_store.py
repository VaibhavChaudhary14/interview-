from typing import Protocol


class Chunk:
    def __init__(self, id: str, text: str, score: float, metadata: dict):
        self.id = id
        self.text = text
        self.score = score
        self.metadata = metadata


class VectorStore(Protocol):
    def upsert(self, collection: str, ids: list[str], embeddings: list[list[float]], metadatas: list[dict], documents: list[str]) -> None: ...
    def query(self, collection: str, query_embedding: list[float], k: int, filter: dict | None = None) -> list[Chunk]: ...
