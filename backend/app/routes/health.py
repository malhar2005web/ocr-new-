from fastapi import APIRouter
from app.core.config import settings
from app.db.database import db
from app.services.parsers.image_ocr import image_ocr_engine
from app.services.llm_verifier import llm_verifier

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def get_health():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": {
            "status": "connected" if db.is_connected else "in_memory_fallback",
            "type": "PostgreSQL"
        },
        "ocr_engine": {
            "tesseract_available": bool(image_ocr_engine.tesseract_cmd),
            "binary_path": image_ocr_engine.tesseract_cmd or "Not detected",
            "pdf_engine": "PyMuPDF (fitz) v1.25.3"
        },
        "llm_auditor": {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "configured": llm_verifier.is_available()
        }
    }

