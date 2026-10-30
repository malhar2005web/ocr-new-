import os
import uuid
import re
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from app.core.config import settings
from app.core.logging import logger
from app.db.database import db
from app.services.ingestor import ingestor
from app.services.classifier import classifier
from app.services.cross_verifier import cross_verifier
from app.services.rag_service import rag_service
from app.schemas.document import RAGQueryRequest

router = APIRouter(prefix="/documents", tags=["Documents"])

def build_frontend_response(doc_record: dict) -> dict:
    """
    Transforms internal DB record into the exact structure expected by DocumentDetailView.jsx.
    """
    norm = doc_record.get("normalized_json") or {}
    meta = doc_record.get("metadata_json") or {}
    tables = meta.get("tables", [])
    raw_text = doc_record.get("raw_text", "")

    detected_dates = re.findall(r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b", raw_text)
    detected_dates = list(dict.fromkeys(detected_dates))[:5]

    kv_pairs = []
    def flatten_for_kv(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (str, int, float)) and v:
                    kv_pairs.append({"key": p.replace("_", " ").title(), "value": str(v)})
                elif isinstance(v, dict):
                    flatten_for_kv(v, p)
    flatten_for_kv(norm)

    return {
        "id": doc_record["id"],
        "document_id": doc_record["id"],
        "filename": doc_record["filename"],
        "file_type": doc_record["file_type"],
        "document_type": doc_record.get("document_type", "unclassified"),
        "status": doc_record.get("status", "completed"),
        "source": {
            "filename": doc_record["filename"],
            "file_type": doc_record["file_type"],
            "file_size": doc_record["file_size"],
            "page_count": doc_record.get("page_count", 1)
        },
        "metadata": {
            "dates": detected_dates,
            "page_count": doc_record.get("page_count", 1)
        },
        "content": {
            "custom_fields": norm,
            "tables": tables,
            "key_value_pairs": kv_pairs[:30]
        },
        "raw_text": raw_text,
        "normalized_json": norm,
        "validation": meta.get("validation", {"status": "completed", "issues": []}),
        "extraction_metadata": meta.get("extraction_metadata", {
            "pdf_method": "pymupdf_native_vector",
            "ocr_engine": "tesseract_v5",
            "model": "deterministic_heuristics",
            "extraction_mode": "deterministic_rules"
        }),
        "created_at": doc_record.get("created_at"),
        "updated_at": doc_record.get("updated_at")
    }

@router.post("/extract")
async def extract_document(
    file: UploadFile = File(...),
    async_mode: Optional[str] = Form("false")
):
    try:
        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}_{file.filename}"
        saved_path = os.path.join(settings.STORAGE_DIR, safe_filename)

        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        file_size = len(content)
        file_ext = Path(file.filename).suffix.lower().lstrip(".")

        # Step 1: Universal Ingestion (PyMuPDF / Tesseract)
        ingest_res = await asyncio.to_thread(ingestor.ingest_file, saved_path)

        # Step 2: Document Classification
        doc_type, conf = classifier.classify(ingest_res["raw_text"])

        # Step 3: Cross-Verification & Dynamic JSON Generation
        cv_res = await asyncio.to_thread(
            cross_verifier.process_and_verify,
            doc_type=doc_type,
            raw_text=ingest_res["raw_text"],
            ocr_tables=ingest_res.get("tables", []),
            pdf_method=ingest_res.get("pdf_method", "native"),
            is_scanned=ingest_res.get("is_scanned", False)
        )

        metadata_payload = {
            "tables": ingest_res.get("tables", []),
            "validation": cv_res["validation"],
            "extraction_metadata": cv_res["extraction_metadata"],
            "classification_confidence": conf
        }

        # Step 4: Index Document Chunks for RAG Q&A
        if ingest_res.get("pages"):
            await rag_service.chunk_and_index_document(doc_id, ingest_res["pages"])

        # Step 5: Save Document in PostgreSQL Database
        doc_record = {
            "id": doc_id,
            "filename": file.filename,
            "file_type": file_ext,
            "file_path": saved_path,
            "file_size": file_size,
            "document_type": doc_type,
            "status": cv_res["validation"]["status"],
            "page_count": ingest_res.get("page_count", 1),
            "raw_text": ingest_res.get("raw_text", ""),
            "normalized_json": cv_res["normalized_json"],
            "metadata_json": metadata_payload
        }

        saved_doc = await db.save_document(doc_record)
        await db.save_audit(doc_id, "ingested_and_extracted", {"document_type": doc_type})

        response_data = build_frontend_response(saved_doc)
        response_data["document_id"] = doc_id
        response_data["message"] = "Document extracted successfully"
        return response_data

    except Exception as e:
        logger.error(f"Extraction failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def list_documents(
    documentType: Optional[str] = Query(None),
    filename: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    fromDate: Optional[str] = Query(None),
    toDate: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    sortBy: str = Query("created_at"),
    sortOrder: str = Query("DESC")
):
    res = await db.list_documents(
        document_type=documentType,
        filename=filename,
        status=status,
        from_date=fromDate,
        to_date=toDate,
        page=page,
        limit=limit,
        sort_by=sortBy,
        sort_order=sortOrder
    )
    return res

@router.get("/{doc_id}")
async def get_document(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return build_frontend_response(doc)

@router.get("/{doc_id}/status")
async def get_document_status(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc["id"],
        "document_id": doc["id"],
        "status": doc.get("status", "completed"),
        "document_type": doc.get("document_type", "unclassified")
    }

@router.get("/{doc_id}/raw")
async def get_raw_text(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return PlainTextResponse(doc.get("raw_text", "No raw text available"))

@router.get("/{doc_id}/download")
async def download_document(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc or not os.path.exists(doc.get("file_path", "")):
        raise HTTPException(status_code=404, detail="Original document file not found on disk")

    media_type = "application/pdf" if doc["file_type"].lower() == "pdf" else f"image/{doc['file_type'].lower()}"
    return FileResponse(
        path=doc["file_path"],
        filename=doc["filename"],
        media_type=media_type
    )

@router.post("/{doc_id}/query")
async def query_document(doc_id: str, payload: RAGQueryRequest):
    return await rag_service.answer_query(doc_id, payload.query)

@router.post("/{doc_id}/reprocess")
async def reprocess_document(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc or not os.path.exists(doc.get("file_path", "")):
        raise HTTPException(status_code=404, detail="Document or file not found")

    ingest_res = await asyncio.to_thread(ingestor.ingest_file, doc["file_path"])
    doc_type, conf = classifier.classify(ingest_res["raw_text"])

    cv_res = await asyncio.to_thread(
        cross_verifier.process_and_verify,
        doc_type=doc_type,
        raw_text=ingest_res["raw_text"],
        ocr_tables=ingest_res.get("tables", []),
        pdf_method=ingest_res.get("pdf_method", "native"),
        is_scanned=ingest_res.get("is_scanned", False)
    )

    metadata_payload = {
        "tables": ingest_res.get("tables", []),
        "validation": cv_res["validation"],
        "extraction_metadata": cv_res["extraction_metadata"],
        "classification_confidence": conf
    }

    doc["document_type"] = doc_type
    doc["status"] = cv_res["validation"]["status"]
    doc["raw_text"] = ingest_res["raw_text"]
    doc["normalized_json"] = cv_res["normalized_json"]
    doc["metadata_json"] = metadata_payload

    updated = await db.save_document(doc)
    await db.save_audit(doc_id, "reprocessed", {"status": doc["status"]})
    return build_frontend_response(updated)

@router.post("/{doc_id}/approve")
async def approve_document(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    meta = doc.get("metadata_json") or {}
    val = meta.get("validation") or {}
    val["status"] = "valid"
    val["issues"] = []
    meta["validation"] = val
    doc["metadata_json"] = meta
    doc["status"] = "valid"

    updated = await db.save_document(doc)
    await db.save_audit(doc_id, "manually_approved", {"user_action": "verified"})
    return build_frontend_response(updated)
