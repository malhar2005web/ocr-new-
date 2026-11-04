import pytest
from app.services.polished_json_service import polished_json_service

def test_polished_json_purchase_books_schema():
    sample_input = {
        "Products": [
            {
                "SrNo": 1,
                "Pcs_Qty": {
                    "pcs": 115,
                    "unit": "Mtr",
                    "quantity": 10821
                },
                "Product": "Rudraksh 52*50-47 BALE[7} BALE NO 394 TO 400 PCS{115}",
                "Product_Details": "HSN 5208",
                "Value_Rate_Product_Amount": {
                    "rate": 22.5,
                    "amount": 243472.5
                }
            }
        ],
        "Supplier": {
            "pan": "AITPD0799E",
            "name": "Mahaprabhuji Textiles",
            "gstin": "27AITPD0799E1ZY",
            "address": "S.No. 26, P.No.25/26/31/32, Dayne Shiwar, Malegaon"
        },
        "Bill_Date": "14-Dec-21",
        "Total_Pcs": 115,
        "Total_Qty": 10821,
        "Invoice_Amount": 255646,
        "Location_Address": {
            "name": "PAWAN PROCESS",
            "address": "DYANE SHIWAR. MALEGAON, DIST. NASHIK, M.S."
        },
        "GRN_No_Bill_No_Voucher_No": "MT/1520",
        "TaxAmt_Tax_Taxable_Amount": {
            "cgst": 6086.81,
            "sgst": 6086.81,
            "total_tax": 12173.62,
            "taxable_amount": 243472.5
        },
        "Other_Information_Remark_Narration_Description_TNC": {
            "buyer": "M.Tarun & Co",
            "remarks": "Interest @18% will be payable for the late payment from the due date.",
            "buyer_gstin": "27AAHFM9152A1ZE"
        }
    }

    res = polished_json_service.generate_polished_json(sample_input)
    assert "Purchase Books" in res
    pb = res["Purchase Books"]

    assert pb["Bill No"] == "MT/1520"
    assert pb["Voucher No"] == "MT/1520"
    assert pb["Bill Date  "] == "14-Dec-21"
    assert pb["Voucher Date  :"] == "14-Dec-21"
    assert pb["Supplier"] == "Mahaprabhuji Textiles"
    assert pb["Product Amount"] == 243472.5
    assert pb["Taxable Amount"] == 243472.5
    assert pb["Total Qty"] == 10821.0
    assert pb["Total Pcs"] == 115
    assert pb["total Tax"] == 12173.62
    assert pb["Invoice Amount"] == 255646.0

    assert len(pb["Product Details"]) == 1
    p = pb["Product Details"][0]
    assert p["SrNo"] == 1
    assert "Rudraksh 52*50-47" in p["Product"]
    assert p["Qty"] == 10821.0
    assert p["Rate"] == 22.5
    assert p["Value"] == 243472.5
    assert p["Pcs"] == 115
    assert "Rudraksh 52*50-47" in p["Quality"]
    assert "BALE NO 394 TO 400" in p["Other Information"]
    assert "PAWAN PROCESS" in p["Location"]
    assert "5208" in p["Chapter Heading"]

    assert pb["cgst"] == 6086.81
    assert pb["sgst"] == 6086.81
