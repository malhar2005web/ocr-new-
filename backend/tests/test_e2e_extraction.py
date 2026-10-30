import os
import pytest
from app.services.ingestor import ingestor
from app.services.classifier import classifier
from app.services.cross_verifier import cross_verifier

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")

def test_extract_real_invoice_pdf():
    pdf_path = os.path.join(TEST_DATA_DIR, "test_invoice.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip("Sample test_invoice.pdf not found")

    # 1. Ingest
    ingest_res = ingestor.ingest_file(pdf_path)
    assert ingest_res["page_count"] >= 1
    assert len(ingest_res["raw_text"]) > 0

    # 2. Classify
    doc_type, conf = classifier.classify(ingest_res["raw_text"])
    assert doc_type == "tax_invoice"

    # 3. Cross-verify & dynamic JSON (synchronous call)
    result = cross_verifier.process_and_verify(
        doc_type=doc_type,
        raw_text=ingest_res["raw_text"],
        ocr_tables=ingest_res.get("tables", []),
        pdf_method=ingest_res.get("pdf_method", "native")
    )

    norm_json = result["normalized_json"]
    assert isinstance(norm_json, dict)
    
    # Verify strict zero-null rules
    import json
    json_str = json.dumps(norm_json)
    assert ": null" not in json_str
    assert '": ""' not in json_str
    assert '": "-"' not in json_str

def test_extract_real_contract_pdf():
    pdf_path = os.path.join(TEST_DATA_DIR, "test_contract.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip("Sample test_contract.pdf not found")

    ingest_res = ingestor.ingest_file(pdf_path)
    doc_type, conf = classifier.classify(ingest_res["raw_text"])
    assert doc_type in ["contract_agreement", "general_document"]

    result = cross_verifier.process_and_verify(
        doc_type=doc_type,
        raw_text=ingest_res["raw_text"],
        ocr_tables=ingest_res.get("tables", [])
    )
    assert isinstance(result["normalized_json"], dict)
