import os
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
from PIL import Image
import io
from app.services.parsers.image_ocr import image_ocr_engine
from app.core.logging import logger

class PDFExtractionEngine:
    def __init__(self):
        pass

    def extract_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Ingests a PDF file, extracting:
        - Full raw text per page
        - Layout blocks and bounding boxes
        - Structured tables
        - Hybrid scan detection (routes scanned pages to OCR)
        """
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_content = []
        all_raw_text = []
        all_tables = []
        is_hybrid_or_scanned = False
        scanned_page_count = 0

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1

            # 1. Native text extraction
            native_text = page.get_text("text").strip()
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

            # Determine if page is a scan / image-only
            char_count = len(native_text)
            is_page_scanned = (char_count < 40)

            page_tables = []
            final_page_text = native_text
            ocr_applied = False

            if is_page_scanned:
                scanned_page_count += 1
                is_hybrid_or_scanned = True
                logger.info(f"Page {page_num} in {os.path.basename(file_path)} detected as scanned (chars={char_count}). Applying OCR.")

                # Render page at 300 DPI for OCR
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_result = image_ocr_engine.extract_text_and_data(img)
                if ocr_result["text"].strip():
                    final_page_text = ocr_result["text"].strip()
                    ocr_applied = True

            # 2. Table extraction using PyMuPDF find_tables
            try:
                tabs = page.find_tables()
                if tabs and tabs.tables:
                    for t_idx, tab in enumerate(tabs.tables):
                        extracted_table = tab.extract()
                        if extracted_table and len(extracted_table) > 1:
                            # First non-empty row as header
                            headers = [str(c or "").strip() for c in extracted_table[0]]
                            rows = []
                            for row_cells in extracted_table[1:]:
                                row_dict = {}
                                for c_idx, cell in enumerate(row_cells):
                                    h_name = headers[c_idx] if c_idx < len(headers) and headers[c_idx] else f"Col_{c_idx+1}"
                                    row_dict[h_name] = str(cell or "").strip()
                                # Only add rows that contain at least one non-empty value
                                if any(v for v in row_dict.values()):
                                    rows.append(row_dict)

                            if rows:
                                table_entry = {
                                    "title": f"Table (Page {page_num}, Index {t_idx + 1})",
                                    "page": page_num,
                                    "headers": headers,
                                    "rows": rows
                                }
                                page_tables.append(table_entry)
                                all_tables.append(table_entry)
            except Exception as e:
                logger.debug(f"Table extraction on page {page_num} encountered: {e}")

            page_dict = {
                "page": page_num,
                "text": final_page_text,
                "is_scanned": is_page_scanned,
                "ocr_applied": ocr_applied,
                "block_count": len(blocks),
                "tables": page_tables
            }
            pages_content.append(page_dict)
            if final_page_text:
                all_raw_text.append(f"--- [PAGE {page_num}] ---\n{final_page_text}")

        full_raw_text = "\n\n".join(all_raw_text)
        pdf_method = (
            "pymupdf_ocr_hybrid" if (scanned_page_count > 0 and scanned_page_count < total_pages)
            else "pymupdf_tesseract_scanned" if scanned_page_count == total_pages
            else "pymupdf_native_vector"
        )

        return {
            "page_count": total_pages,
            "raw_text": full_raw_text,
            "pages": pages_content,
            "tables": all_tables,
            "pdf_method": pdf_method,
            "scanned_page_count": scanned_page_count,
            "is_scanned": is_hybrid_or_scanned
        }

pdf_engine = PDFExtractionEngine()

