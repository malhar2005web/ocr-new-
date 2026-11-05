import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import db

client = TestClient(app)

@pytest.mark.anyio
async def test_purchase_books_api_by_sr_no_and_id():
    # Save a test document in DB
    test_doc = {
        "id": "test-uuid-pb-999",
        "sr_no": 999,
        "filename": "test_purchase_order.pdf",
        "file_type": "pdf",
        "file_path": "/fake/path/test_purchase_order.pdf",
        "file_size": 1024,
        "document_type": "tax_invoice",
        "status": "completed",
        "page_count": 1,
        "raw_text": "Sample invoice text Voucher No MT/1520 Date 14-Dec-21 Supplier Mahaprabhuji Textiles",
        "normalized_json": {
            "invoice_number": "MT/1520",
            "invoice_date": "14-Dec-21",
            "supplier": {"name": "Mahaprabhuji Textiles"},
            "grand_total": 255646.0
        },
        "metadata_json": {}
    }
    await db.save_document(test_doc)

    # 1. Test GET by SR NO: /api/v1/purchase-books/999
    res_sr = client.get("/api/v1/purchase-books/999")
    assert res_sr.status_code == 200
    data_sr = res_sr.json()
    assert "Purchase Books" in data_sr
    pb_sr = data_sr["Purchase Books"]
    assert "Voucher No" in pb_sr
    assert "Supplier" in pb_sr
    assert pb_sr["Voucher No"] == "MT/1520"

    # 2. Test GET by UUID: /api/v1/purchase-books/test-uuid-pb-999
    res_uuid = client.get("/api/v1/purchase-books/test-uuid-pb-999")
    assert res_uuid.status_code == 200
    data_uuid = res_uuid.json()
    assert "Purchase Books" in data_uuid
    assert data_uuid["Purchase Books"]["Voucher No"] == "MT/1520"

    # 3. Test GET on /api/v1/documents/999/purchase-books
    res_sub = client.get("/api/v1/documents/999/purchase-books")
    assert res_sub.status_code == 200
    assert "Purchase Books" in res_sub.json()

    # 4. Test 404 for non-existent document
    res_404 = client.get("/api/v1/purchase-books/999999999")
    assert res_404.status_code == 404
