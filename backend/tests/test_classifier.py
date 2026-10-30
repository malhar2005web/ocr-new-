import pytest
from app.services.classifier import classifier

def test_classify_tax_invoice():
    sample_text = (
        "TAX INVOICE\n"
        "Skyway RMC Ready Mix Concrete\n"
        "GSTIN: 27AAPCS9384K1Z0\n"
        "Invoice No: INV-2026-001\n"
        "HSN/SAC: 38245010\n"
        "CGST 9% SGST 9% Total Taxable Value: 45000.00"
    )
    doc_type, conf = classifier.classify(sample_text)
    assert doc_type == "tax_invoice"
    assert conf >= 0.7

def test_classify_agreement():
    sample_text = (
        "SERVICE AGREEMENT\n"
        "This Agreement is made by and between Party A and Party B.\n"
        "WHEREAS the parties desire to enter into this contract...\n"
        "NOW THEREFORE, in witness whereof, the parties agree to the following terms and conditions..."
    )
    doc_type, conf = classifier.classify(sample_text)
    assert doc_type == "contract_agreement"
    assert conf >= 0.7

def test_classify_bank_statement():
    sample_text = (
        "HDFC BANK STATEMENT OF ACCOUNT\n"
        "Account Number: 50100234567890\n"
        "Opening Balance: 1,45,000.00\n"
        "Closing Balance: 2,10,000.00\n"
        "Withdrawal: 5,000.00 Deposit: 70,000.00"
    )
    doc_type, conf = classifier.classify(sample_text)
    assert doc_type == "bank_statement"
    assert conf >= 0.7

