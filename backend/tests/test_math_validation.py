import pytest
from app.services.validator import validator

def test_math_validation_perfect_invoice():
    data = {
        "goods_and_tax_details": {
            "items": [
                {"description": "Item A", "quantity": "2", "rate": "100.00", "amount": "200.00"},
                {"description": "Item B", "quantity": "5", "rate": "50.00", "amount": "250.00"}
            ],
            "taxable_value": "450.00",
            "tax_details": {
                "cgst": "40.50",
                "sgst": "40.50",
                "total_tax": "81.00"
            },
            "total_amount_after_tax": "531.00"
        }
    }
    result = validator.validate_document("tax_invoice", data)
    assert result["status"] == "valid"
    assert len(result["issues"]) == 0

def test_math_validation_detects_item_mismatch():
    data = {
        "goods_and_tax_details": {
            "items": [
                # 2 * 100 != 250 (discrepancy)
                {"description": "Item A", "quantity": "2", "rate": "100.00", "amount": "250.00"}
            ],
            "taxable_value": "250.00",
            "total_amount_after_tax": "250.00"
        }
    }
    result = validator.validate_document("tax_invoice", data)
    assert result["status"] == "review_needed"
    assert len(result["issues"]) > 0
    assert result["issues"][0]["issue_type"] == "arithmetic_mismatch"
    assert result["issues"][0]["expected"] == 200.0
    assert result["issues"][0]["actual"] == 250.0

def test_math_validation_detects_grand_total_mismatch():
    data = {
        "goods_and_tax_details": {
            "items": [
                {"description": "Item A", "quantity": "1", "rate": "100.00", "amount": "100.00"}
            ],
            "taxable_value": "100.00",
            "tax_details": {"total_tax": "18.00"},
            # Expected 118.00, reported 150.00
            "total_amount_after_tax": "150.00"
        }
    }
    result = validator.validate_document("tax_invoice", data)
    assert result["status"] == "review_needed"
    issue_types = [i["issue_type"] for i in result["issues"]]
    assert "grand_total_mismatch" in issue_types

