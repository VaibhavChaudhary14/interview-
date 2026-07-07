#!/usr/bin/env python3
"""
Knowledge Base Ingestion CLI

Usage:
    python scripts/ingest_knowledge_base.py --role backend_engineer
    python scripts/ingest_knowledge_base.py --role ai_ml_engineer
    python scripts/ingest_knowledge_base.py --role backend_engineer --kb-dir /path/to/knowledge_base

Place role-specific PDFs in:
    backend/data/knowledge_base/<role_slug>/

This chunks each document, generates embeddings, and upserts them into
a role-scoped Chroma collection: kb_<role_slug>
"""
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_ROLES = ["backend_engineer", "ai_ml_engineer"]


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base PDFs into ChromaDB")
    parser.add_argument(
        "--role",
        required=True,
        choices=SUPPORTED_ROLES,
        help="Role slug to ingest (e.g., backend_engineer)",
    )
    parser.add_argument(
        "--kb-dir",
        type=Path,
        default=None,
        help="Path to knowledge_base root directory (default: data/knowledge_base relative to backend root)",
    )
    args = parser.parse_args()

    # Import app modules after argparse so help text works without app env
    from app.core.config import settings
    from app.rag.ingestion import ingest_knowledge_base
    from app.rag.chroma_store import ChromaStore
    from sentence_transformers import SentenceTransformer

    # Resolve knowledge base directory
    if args.kb_dir:
        kb_dir = args.kb_dir
    else:
        # Default: data/knowledge_base relative to the backend app root
        script_dir = Path(__file__).resolve().parent
        backend_root = script_dir.parent
        kb_dir = backend_root / "data" / "knowledge_base"

    role = args.role
    role_dir = kb_dir / role

    if not kb_dir.exists():
        logger.error("Knowledge base root not found: %s", kb_dir)
        logger.error("Create it and place PDFs at: %s/<role_slug>/*.pdf", kb_dir)
        sys.exit(1)

    if not role_dir.exists():
        logger.error("Role directory not found: %s", role_dir)
        logger.error("Create it and add PDFs: %s/*.pdf", role_dir)
        sys.exit(1)

    pdfs = list(role_dir.glob("*.pdf"))
    if not pdfs:
        logger.error("No PDFs found in %s", role_dir)
        logger.error("Add PDF files for role '%s' and re-run.", role)
        sys.exit(1)

    logger.info("Found %d PDF(s) for role '%s': %s", len(pdfs), role, [p.name for p in pdfs])
    logger.info("Loading embedding model: %s (this may take a moment on first run)", settings.embedding_model)

    embedder = SentenceTransformer(settings.embedding_model)
    vector_store = ChromaStore()

    logger.info("Ingesting into ChromaDB at: %s", settings.vector_store_path)
    ingest_knowledge_base(role_slug=role, kb_dir=kb_dir, vector_store=vector_store, embedder=embedder)

    logger.info("✓ Ingestion complete for role '%s'", role)
    logger.info("  Collection name: kb_%s", role)


if __name__ == "__main__":
    main()
