from fastapi import APIRouter, Depends
from pathlib import Path
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.role_family import RoleFamily
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


@router.get("/role-families")
def list_role_families(db: DBSession = Depends(get_db)):
    """
    Returns all seeded role families for the browse grid. Each family links
    to 3 difficulty levels, matching the edesy.in-style browse-by-technology
    layout.
    """
    families = db.query(RoleFamily).order_by(RoleFamily.name).all()
    return {
        "families": [
            {
                "slug": f.slug,
                "name": f.name,
                "description": f.description,
                "has_kb": f.kb_collection_name is not None,
            }
            for f in families
        ]
    }

