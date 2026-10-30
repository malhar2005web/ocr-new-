import re
from typing import Dict, Any, Tuple
from app.core.logging import logger

CLASSIFICATION_PATTERNS = {
    "tax_invoice": [
        r"\btax\s+invoice\b", r"\bgst\s+invoice\b", r"\binvoice\s+no\b",
        r"\bgstin\b", r"\bhsn\s*/?\s*sac\b", r"\bcgst\b", r"\bsgst\b", r"\bigst\b",
        r"\bbill\s+to\b", r"\bship\s+to\b", r"\btaxable\s+value\b"
    ],
    "delivery_challan": [
        r"\bdelivery\s+challan\b", r"\bdispatch\s+challan\b", r"\bchallan\s+no\b",
        r"\btransporter\b", r"\bvehicle\s+no\b", r"\blr\s+no\b", r"\bconsignee\b"
    ],
    "purchase_order": [
        r"\bpurchase\s+order\b", r"\bpo\s+number\b", r"\bp\.o\.\s*no\b",
        r"\bvendor\s+code\b", r"\border\s+date\b", r"\bquotation\s+ref\b"
    ],
    "bill_receipt": [
        r"\breceipt\b", r"\bcash\s+bill\b", r"\bmoney\s+receipt\b",
        r"\bpayment\s+received\b", r"\bcounterfoil\b"
    ],
    "contract_agreement": [
        r"\bagreement\b", r"\bmemorandum\s+of\s+understanding\b", r"\bmou\b",
        r"\bby\s+and\s+between\b", r"\bwhereas\b", r"\bnow\s+therefore\b",
        r"\bindemnif\w+\b", r"\bjurisdiction\b", r"\bseverability\b",
        r"\bin\s+witness\s+whereof\b", r"\bterms\s+and\s+conditions\b"
    ],
    "bank_statement": [
        r"\bbank\s+statement\b", r"\bstatement\s+of\s+account\b",
        r"\baccount\s+number\b", r"\bopening\s+balance\b", r"\bclosing\s+balance\b",
        r"\bwithdrawal\b", r"\bdeposit\b", r"\bcheque\s+no\b", r"\btransaction\s+date\b"
    ],
    "legal_document": [
        r"\baffidavit\b", r"\bpower\s+of\s+attorney\b", r"\bdeed\b",
        r"\bnotary\s+public\b", r"\bpetitioner\b", r"\brespondent\b", r"\bcourt\b"
    ]
}

class DocumentClassifier:
    def classify(self, text: str) -> Tuple[str, float]:
        """
        Determines the document category and classification confidence score.
        Never forces an invoice schema if text does not support it.
        """
        if not text or len(text.strip()) < 20:
            return "general_document", 0.3

        lower_text = text.lower()
        scores = {}

        for doc_type, patterns in CLASSIFICATION_PATTERNS.items():
            match_count = 0
            for pat in patterns:
                if re.search(pat, lower_text):
                    match_count += 1
            if match_count > 0:
                scores[doc_type] = match_count

        if not scores:
            return "general_document", 0.5

        best_type, count = max(scores.items(), key=lambda x: x[1])
        total_patterns = len(CLASSIFICATION_PATTERNS[best_type])
        confidence = min(1.0, round(0.4 + (count / total_patterns) * 0.6, 2))

        logger.info(f"Classified document as '{best_type}' with confidence {confidence} (matched {count} signals).")
        return best_type, confidence

classifier = DocumentClassifier()

