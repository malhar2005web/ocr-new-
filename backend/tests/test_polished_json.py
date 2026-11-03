import pytest
from app.services.polished_json_service import polished_json_service

def test_polished_json_mapping_full_sample():
    universal_sample = {
        "invoice_number": "SA-992",
        "invoice_date": "07/10/2026",
        "supplier": {
            "name": "SHREE NAKODA TEXTILES",
            "address": "Bldg No-6, Kapadia Bldg, 1st Flr, Kalbadevi, Mumbai - 400002",
            "gstin": "27AAJPJ2227M1ZJ",
            "pan": "AAJPJ2227M"
        },
        "consignee": {
            "name": "SHREE JEENMATA DYE & PTG MILLS PVT LTD",
            "address": "PLOT NO.A-44, MIDC BADLAPUR, BADLAPUR 421503",
            "gstin": "27AAHCS1877P1ZJ"
        },
        "buyer": {
            "name": "M/s M TARUN AND CO.",
            "gstin": "27AAHFM9152A1ZE"
        },
        "discount": "4587.22",
        "line_items": [
            {
                "sr_no": 1,
                "product_name": "SAMLL SALLY GADWAL 2218",
                "hsn_code": "520811",
                "lot_no": "547",
                "pieces": 48,
                "quantity": 5201.30,
                "unit": "MTR.",
                "rate_per_unit": 29.40,
                "amount": 152918.22
            }
        ],
        "bank_details": {
            "bank_name": "KOTAK MAHINDRA BANK",
            "branch": "NEW MARIN LINES MUMBAI",
            "account_number": "2413240134",
            "ifsc": "KKBK0001350"
        },
        "taxable_value": 148331.00,
        "cgst_amount": 3708.00,
        "sgst_amount": 3708.00,
        "igst_amount": 0.00,
        "total_gst": 7416.00,
        "grand_total": 155747.00
    }

    polished = polished_json_service.generate_polished_json(universal_sample)

    assert polished["GRN_No_Bill_No_Voucher_No"] == "SA-992"
    assert polished["Bill_Date"] == "07/10/2026"
    assert polished["Supplier"]["name"] == "SHREE NAKODA TEXTILES"
    assert polished["Supplier"]["gstin"] == "27AAJPJ2227M1ZJ"
    
    assert len(polished["Products"]) == 1
    p = polished["Products"][0]
    assert p["SrNo"] == 1
    assert p["Product"] == "SAMLL SALLY GADWAL 2218"
    assert "HSN 520811" in p["Product_Details"]
    assert "Lot No. 547" in p["Product_Details"]
    assert p["Value_Rate_Product_Amount"]["rate"] == 29.40
    assert p["Value_Rate_Product_Amount"]["amount"] == 152918.22
    assert p["Pcs_Qty"]["pcs"] == 48
    assert p["Pcs_Qty"]["quantity"] == 5201.30
    assert p["Pcs_Qty"]["unit"] == "MTR."

    # Location Address (Consignee mapping)
    assert polished["Location_Address"]["name"] == "SHREE JEENMATA DYE & PTG MILLS PVT LTD"
    assert polished["Location_Address"]["gstin"] == "27AAHCS1877P1ZJ"

    # Other Information
    other = polished["Other_Information_Remark_Narration_Description_TNC"]
    assert other["discount"] == 4587.22
    assert other["buyer"] == "M/s M TARUN AND CO."
    assert other["buyer_gstin"] == "27AAHFM9152A1ZE"
    assert other["bank_details"]["bank_name"] == "KOTAK MAHINDRA BANK"

    # Taxes
    assert polished["TaxAmt_Tax_Taxable_Amount"]["taxable_amount"] == 148331.00
    assert polished["TaxAmt_Tax_Taxable_Amount"]["cgst"] == 3708.00
    assert polished["TaxAmt_Tax_Taxable_Amount"]["sgst"] == 3708.00
    assert polished["TaxAmt_Tax_Taxable_Amount"]["total_tax"] == 7416.00

    # Invoice Amount & Totals
    assert polished["Invoice_Amount"] == 155747.00
    assert polished["Total_Qty"] == 5201.30
    assert polished["Total_Pcs"] == 48
