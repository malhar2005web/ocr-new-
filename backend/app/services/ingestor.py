import os
from pathlib import Path
from typing import Dict, Any
from PIL import Image
from app.services.parsers.pdf_parser import pdf_engine
from app.services.parsers.image_ocr import image_ocr_engine
from app.core.logging import logger

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}

class UniversalIngestionRouter:
    """
    Ingestion router specialized in high-fidelity PDF and Image extraction.
    """
    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        ext = p.suffix.lower()
        file_size = os.path.getsize(file_path)

        if ext in SUPPORTED_PDF_EXTENSIONS:
            logger.info(f"Ingesting PDF document: {p.name}")
            pdf_data = pdf_engine.extract_pdf(file_path)
            return {
                "filename": p.name,
                "file_type": "pdf",
                "file_size": file_size,
                "page_count": pdf_data["page_count"],
                "raw_text": pdf_data["raw_text"],
                "tables": pdf_data["tables"],
                "pdf_method": pdf_data["pdf_method"],
                "is_scanned": pdf_data["is_scanned"],
                "pages": pdf_data["pages"]
            }

        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            logger.info(f"Ingesting Image document: {p.name}")
            with Image.open(file_path) as img:
                ocr_data = image_ocr_engine.extract_text_and_data(img)

            # Package image as a 1-page document
            raw_text = f"--- [PAGE 1] ---\n{ocr_data['text']}" if ocr_data["text"] else ""
            return {
                "filename": p.name,
                "file_type": ext.lstrip("."),
                "file_size": file_size,
                "page_count": 1,
                "raw_text": raw_text,
                "tables": [],
                "pdf_method": "direct_image_ocr",
                "is_scanned": True,
                "confidence": ocr_data.get("confidence", 0.0),
                "pages": [{
                    "page": 1,
                    "text": ocr_data["text"],
                    "is_scanned": True,
                    "ocr_applied": True,
                    "tables": []
                }]
            }

        else:
            raise ValueError(
                f"Unsupported file format '{ext}'. The universal engine supports PDF (.pdf) "
                f"and Image formats ({', '.join(SUPPORTED_IMAGE_EXTENSIONS)})."
            )

ingestor = UniversalIngestionRouter()

