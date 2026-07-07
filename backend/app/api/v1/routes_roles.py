from fastapi import APIRouter
from pathlib import Path
from app.core.config import settings

router = APIRouter(tags=["roles"])

ROLES = [
    {"slug": "backend_engineer", "label": "Backend Engineer"},
    {"slug": "ai_ml_engineer", "label": "AI/ML Engineer"},
]


@router.get("/roles")
def get_roles():
    kb_base = Path(settings.vector_store_path).parent / "knowledge_base"
    results = []
    for role in ROLES:
        role_dir = kb_base / role["slug"]
        kb_ready = role_dir.exists() and any(role_dir.glob("*.pdf"))
        results.append({**role, "kb_ready": kb_ready})
    return {"roles": results}
