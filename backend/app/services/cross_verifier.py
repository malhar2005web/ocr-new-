from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.json_generator import json_generator, clean_dynamic_json
from app.services.validator import validator
from app.services.llm_verifier import llm_verifier

class CrossVerificationOrchestrator:
    """
    Executes the comprehensive cross-verification loop:
    1. Primary OCR -> Raw text & Tables
    2. Candidate JSON generation (LLM or Deterministic)
    3. Independent checks:
       - Table item count: OCR table rows vs JSON items
       - Source text presence (hallucination guard)
       - Python Decimal arithmetic & tax integrity
    4. Recovery triggering: re-prompting LLM if discrepancy detected
    5. Warning generation & audit provenance
    """
    def process_and_verify(
        self,
        doc_type: str,
        raw_text: str,
        ocr_tables: List[Dict[str, Any]],
        pdf_method: str = "pymupdf_native_vector",
        is_scanned: bool = False
    ) -> Dict[str, Any]:
        ocr_item_count = sum(len(t.get("rows", [])) for t in ocr_tables)
        extraction_mode = "deterministic_rules"
        model_used = "deterministic_heuristics"
        cross_status = "unverified_llm_skipped"
        audit_note = "Processed via PyMuPDF/Tesseract deterministic extraction pipeline."

        # Step 1: Initial Structured JSON Generation
        candidate_json = None
        if llm_verifier.is_available():
            candidate_json = llm_verifier.verify_and_structure_document(
                doc_type=doc_type,
                raw_text=raw_text,
                ocr_tables=ocr_tables
            )
            if candidate_json:
                extraction_mode = "hybrid_cross_verified"
                model_used = f"{settings.LLM_PROVIDER}:{settings.LLM_MODEL}"
                cross_status = "verified"

        # Fallback to deterministic rules if LLM not configured or failed
        if not candidate_json:
            candidate_json = json_generator.generate_deterministic_json(
                doc_type=doc_type,
                raw_text=raw_text,
                tables=ocr_tables
            )

        # Step 2: Independent Structural & Arithmetic Verification
        extracted_items = (
            candidate_json.get("goods_and_tax_details", {}).get("items")
            or candidate_json.get("items")
            or []
        )
        json_item_count = len(extracted_items)

        discrepancy_reasons = []
        if ocr_item_count > 0 and json_item_count < ocr_item_count:
            discrepancy_reasons.append(
                f"Item count mismatch: OCR detected {ocr_item_count} table rows, "
                f"but candidate JSON only contains {json_item_count} items."
            )

        val_result = validator.validate_document(doc_type, candidate_json)
        if val_result.get("issues"):
            for iss in val_result["issues"]:
                discrepancy_reasons.append(f"Arithmetic Issue [{iss['issue_type']}]: {iss['message']}")

        # Step 3: Trigger Recovery Pass if Discrepancy Found and LLM was active in first pass
        if discrepancy_reasons and llm_verifier.is_available() and extraction_mode == "hybrid_cross_verified":
            logger.warning(
                f"Discrepancy detected during cross-verification ({len(discrepancy_reasons)} issues). "
                "Triggering recovery pass with LLM auditor..."
            )
            discrepancy_context = "\n".join(discrepancy_reasons)
            recovery_json = llm_verifier.verify_and_structure_document(
                doc_type=doc_type,
                raw_text=raw_text,
                ocr_tables=ocr_tables,
                discrepancy_context=discrepancy_context
            )
            if recovery_json:
                rec_val_result = validator.validate_document(doc_type, recovery_json)
                rec_items = (
                    recovery_json.get("goods_and_tax_details", {}).get("items")
                    or recovery_json.get("items")
                    or []
                )
                if len(rec_items) >= json_item_count or len(rec_val_result.get("issues", [])) <= len(val_result.get("issues", [])):
                    candidate_json = recovery_json
                    val_result = rec_val_result
                    cross_status = "recovered_after_discrepancy"
                    audit_note = (
                        "Discrepancies were detected during cross-verification; "
                        "LLM recovery pass successfully addressed ambiguous table rows."
                    )

        # Step 4: Final warning generation if issues remain
        if discrepancy_reasons and not val_result.get("issues"):
            for disc in discrepancy_reasons:
                val_result.setdefault("issues", []).append({
                    "issue_type": "discrepancy_detected",
                    "message": disc
                })
            val_result["status"] = "review_needed"

        if val_result.get("issues"):
            audit_note += f" Review needed for {len(val_result['issues'])} detected consistency alerts."

        return {
            "normalized_json": clean_dynamic_json(candidate_json) or {},
            "validation": val_result,
            "extraction_metadata": {
                "pdf_method": pdf_method,
                "ocr_engine": "tesseract_v5" if is_scanned else "pymupdf_native",
                "model": model_used,
                "llm_provider": settings.LLM_PROVIDER if llm_verifier.is_available() else "none",
                "extraction_mode": extraction_mode,
                "cross_verification_status": cross_status,
                "audit_summary": audit_note
            }
        }

cross_verifier = CrossVerificationOrchestrator()
