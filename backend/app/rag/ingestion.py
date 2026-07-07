import hashlib
import logging
from pathlib import Path
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import torch

# Limit PyTorch CPU threads to avoid Docker CPU scheduling overhead
torch.set_num_threads(4)

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: Path) -> str:
    import pypdfium2 as pdfium
    text = ""
    doc = pdfium.PdfDocument(str(path))
    for page in doc:
        textpage = page.get_textpage()
        text += textpage.get_text_range() or ""
    return text


def clean_text(text: str) -> str:
    import re
    text = re.sub(r"(?m)^\s*Page\s+\d+\s*$", "", text)
    text = re.sub(r"(?m)^[\s\-_]{10,}.*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def chunk_id(source_doc: str, chunk_index: int) -> str:
    raw = f"{source_doc}::chunk_{chunk_index:04d}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def ingest_knowledge_base(role_slug: str, kb_dir: Path, vector_store, embedder: SentenceTransformer) -> None:
    collection = f"kb_{role_slug}"
    role_dir = kb_dir / role_slug
    if not role_dir.exists():
        logger.error("Knowledge base directory not found: %s", role_dir)
        return

    pdfs = list(role_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs found in %s", role_dir)
        return

    for pdf_path in pdfs:
        source_doc = pdf_path.stem
        raw = extract_text_from_pdf(pdf_path)
        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned)
        logger.info("PDF %s: %d chunks", pdf_path.name, len(chunks))

        pdf_ids: list[str] = []
        pdf_embeddings: list[list[float]] = []
        pdf_metadatas: list[dict] = []
        pdf_docs: list[str] = []
        doc_chunks = []

        for i, chunk in enumerate(chunks):
            cid = chunk_id(source_doc, i)
            pdf_ids.append(cid)
            pdf_metadatas.append({
                "source_doc": source_doc,
                "page": i,
                "chunk_index": i,
            })
            pdf_docs.append(chunk)
            doc_chunks.append(chunk)

        if doc_chunks:
            logger.info("Encoding %d chunks...", len(doc_chunks))
            embeddings = embedder.encode(doc_chunks, batch_size=32, show_progress_bar=True)
            pdf_embeddings.extend(embeddings.tolist())

            vector_store.upsert(collection, pdf_ids, pdf_embeddings, pdf_metadatas, pdf_docs)
            logger.info("Progressively ingested %d chunks from '%s' into collection '%s'", len(pdf_ids), pdf_path.name, collection)
