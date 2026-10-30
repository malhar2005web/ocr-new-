import pytest
from app.services.json_generator import clean_dynamic_json

def test_clean_dynamic_json_purges_nulls_and_empty_placeholders():
    raw_data = {
        "seller_name": "ABC Corp",
        "gstin": "27AAPFU0939F1ZV",
        "missing_phone": None,
        "empty_string": "",
        "whitespace_string": "   ",
        "dash_placeholder": "-",
        "double_dash": "--",
        "na_placeholder": "N/A",
        "empty_list": [],
        "empty_dict": {},
        "nested_section": {
            "bank_name": "HDFC Bank",
            "account_number": None,
            "branch": "Mumbai",
            "unused_sub": {
                "val": None
            }
        },
        "items": [
            {"description": "Item 1", "price": "100", "notes": "-"},
            {"description": "", "price": None}
        ]
    }

    cleaned = clean_dynamic_json(raw_data)

    assert "seller_name" in cleaned
    assert "gstin" in cleaned
    assert "missing_phone" not in cleaned
    assert "empty_string" not in cleaned
    assert "whitespace_string" not in cleaned
    assert "dash_placeholder" not in cleaned
    assert "double_dash" not in cleaned
    assert "na_placeholder" not in cleaned
    assert "empty_list" not in cleaned
    assert "empty_dict" not in cleaned

    assert cleaned["nested_section"] == {
        "bank_name": "HDFC Bank",
        "branch": "Mumbai"
    }

    assert cleaned["items"] == [
        {"description": "Item 1", "price": "100"}
    ]

