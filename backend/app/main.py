import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppException
from app.api.v1.routes_resume import router as resume_router
from app.api.v1.routes_sessions import router as sessions_router
from app.api.v1.routes_interview import router as interview_router
from app.api.v1.routes_reports import router as reports_router
from app.api.v1.routes_roles import router as roles_router
from app.api.v1.routes_consent import router as consent_router
from app.api.v1.routes_audio import router as audio_router
from app.api.v1.routes_analytics import router as analytics_router

setup_logging()
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        logger.info("Sentry initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Sentry: %s", e)


app = FastAPI(
    title="Candidate Screening System",
    description="AI-Powered Role-Based Candidate Screening with RAG",
    version="0.1.0",
)

# CORS — allow Next.js frontend (dev and Docker)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred.", "details": {}},
    )


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.env}


app.include_router(roles_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(interview_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(consent_router, prefix="/api/v1")
app.include_router(audio_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
