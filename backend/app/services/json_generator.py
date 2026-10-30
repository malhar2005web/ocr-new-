import re
from typing import Any, Dict, List, Optional
from app.core.logging import logger

DISALLOWED_PLACEHOLDERS = {"-", "--", "---", "n/a", "na", "null", "none", "nil", "undefined"}

def is_empty_value(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if not cleaned or cleaned in DISALLOWED_PLACEHOLDERS:
            return True
    if isinstance(val, (list, tuple, set)) and len(val) == 0:
        return True
    if isinstance(val, dict) and len(val) == 0:
        return True
    return False

def clean_dynamic_json(data: Any) -> Any:
    """
    Recursively purges all nulls, empty strings, placeholders ('-', 'N/A'),
    empty arrays, and empty dictionaries from the data structure.
    Ensures zero unwanted nulls or empty placeholders exist in the output JSON.
    """
    if isinstance(data, dict):
        cleaned_dict = {}
        for k, v in data.items():
            if is_empty_value(v):
                continue
            cleaned_v = clean_dynamic_json(v)
            if not is_empty_value(cleaned_v):
                cleaned_dict[k] = cleaned_v
        return cleaned_dict if cleaned_dict else None

    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            if is_empty_value(item):
                continue
            cleaned_item = clean_dynamic_json(item)
            if not is_empty_value(cleaned_item):
                cleaned_list.append(cleaned_item)
        return cleaned_list if cleaned_list else None

    elif isinstance(data, str):
        stripped = data.strip()
        if not stripped or stripped.lower() in DISALLOWED_PLACEHOLDERS:
            return None
        return stripped

    return data

class DynamicJSONGenerator:
    """
    Constructs adaptive structured JSON according to the document type.
    Enforces strict omission of any missing or absent fields.
    """
    def generate_deterministic_json(
        self,
        doc_type: str,
        raw_text: str,
        tables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        result = {}

        if doc_type in ["tax_invoice", "purchase_order", "delivery_challan", "bill_receipt"]:
            result = self._extract_invoice_challan_structure(raw_text, tables, doc_type)
        elif doc_type in ["contract_agreement", "legal_document"]:
            result = self._extract_agreement_structure(raw_text)
        elif doc_type == "bank_statement":
            result = self._extract_bank_statement_structure(raw_text, tables)
        else:
            result = self._extract_general_document_structure(raw_text, tables)

        cleaned = clean_dynamic_json(result) or {}
        return cleaned

    def _extract_invoice_challan_structure(
        self,
        text: str,
        tables: List[Dict[str, Any]],
        doc_type: str
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # 1. Invoice / Document metadata
        inv_meta = {}
        inv_no_match = re.search(r"(?:invoice\s*no|inv\s*no|bill\s*no|challan\s*no)\s*[:.\-]?\s*([A-Za-z0-9\-\/]+)", text, re.I)
        if inv_no_match:
            inv_meta["invoice_number"] = inv_no_match.group(1).strip()

        date_match = re.search(r"(?:invoice\s*date|dated|date|bill\s*date)\s*[:.\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", text, re.I)
        if date_match:
            inv_meta["invoice_date"] = date_match.group(1).strip()

        po_match = re.search(r"(?:po\s*no|po\s*number|order\s*no|buyer\'?s?\s*order\s*no)\s*[:.\-]?\s*([A-Za-z0-9\-\/]+)", text, re.I)
        if po_match:
            inv_meta["po_number"] = po_match.group(1).strip()

        vehicle_match = re.search(r"(?:vehicle\s*no|truck\s*no|motor\s*vehicle\s*no)\s*[:.\-]?\s*([A-Za-z0-9\-]+)", text, re.I)
        if vehicle_match:
            inv_meta["vehicle_number"] = vehicle_match.group(1).strip()

        if inv_meta:
            data["invoice_details"] = inv_meta

        # 2. Seller details
        seller = {}
        gstin_matches = re.findall(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b", text)
        pan_matches = re.findall(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", text)

        if gstin_matches:
            seller["gstin"] = gstin_matches[0]
        if pan_matches:
            seller["pan"] = pan_matches[0]

        lines = [line.strip() for line in text.split("\n") if line.strip() and not line.startswith("---")]
        if lines:
            first_candidate = lines[0]
            if not re.search(r"tax\s+invoice|original|duplicate|page", first_candidate, re.I):
                seller["business_name"] = first_candidate

        if seller:
            data["seller_details"] = seller

        # 3. Buyer details
        buyer = {}
        if len(gstin_matches) > 1:
            buyer["gstin"] = gstin_matches[1]
        if len(pan_matches) > 1 and pan_matches[1] != seller.get("pan"):
            buyer["pan"] = pan_matches[1]

        buyer_block = re.search(r"(?:billed\s*to|buyer|consignee|bill\s*to)\s*[:.\-]?\s*([^\n\r]+)", text, re.I)
        if buyer_block:
            candidate_buyer = buyer_block.group(1).strip()
            if len(candidate_buyer) > 3 and not candidate_buyer.startswith(":"):
                buyer["company_name"] = candidate_buyer

        if buyer:
            data["buyer_details"] = buyer

        # 4. Bank details
        bank = {}
        bank_name_match = re.search(r"(?:bank\s*name|bank)\s*[:.\-]?\s*([^\n\r,]+)", text, re.I)
        if bank_name_match:
            b_cand = bank_name_match.group(1).strip()
            if len(b_cand) > 3 and not any(w in b_cand.lower() for w in ["account", "ifsc", "branch"]):
                bank["bank_name"] = b_cand

        acc_match = re.search(r"(?:a\/c\s*no|acc\s*no|account\s*no|account\s*number)\s*[:.\-]?\s*([0-9]{9,18})", text, re.I)
        if acc_match:
            bank["account_number"] = acc_match.group(1).strip()

        ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)
        if ifsc_match:
            bank["ifsc_code"] = ifsc_match.group(1).strip()

        branch_match = re.search(r"(?:branch)\s*[:.\-]?\s*([^\n\r,]+)", text, re.I)
        if branch_match:
            bank["branch"] = branch_match.group(1).strip()

        if bank:
            data["our_bank_details"] = bank

        # 5. Goods and Taxes from extracted tables
        items = []
        if tables:
            for tbl in tables:
                for r in tbl.get("rows", []):
                    desc = None
                    qty = None
                    rate = None
                    amt = None
                    hsn = None

                    for k, v in r.items():
                        kl = k.lower()
                        if any(w in kl for w in ["description", "item", "particulars", "goods"]):
                            desc = v
                        elif any(w in kl for w in ["qty", "quantity"]):
                            qty = v
                        elif any(w in kl for w in ["rate", "price", "unit"]):
                            rate = v
                        elif any(w in kl for w in ["amount", "total", "taxable"]):
                            amt = v
                        elif any(w in kl for w in ["hsn", "sac"]):
                            hsn = v

                    if desc and not any(w in str(desc).lower() for w in ["total", "cgst", "sgst", "subtotal"]):
                        item_obj = {"description": str(desc)}
                        if qty:
                            item_obj["quantity"] = str(qty)
                        if rate:
                            item_obj["rate"] = str(rate)
                        if amt:
                            item_obj["amount"] = str(amt)
                        if hsn:
                            item_obj["hsn_code"] = str(hsn)
                        items.append(item_obj)

        goods_and_taxes = {}
        if items:
            goods_and_taxes["items"] = items

        grand_match = re.search(r"(?:grand\s*total|total\s*amount|final\s*amount|payable\s*amount)\s*[:.\-]?\s*([0-9,]+\.?[0-9]*)", text, re.I)
        if grand_match:
            goods_and_taxes["total_amount_after_tax"] = grand_match.group(1).replace(",", "").strip()

        taxable_match = re.search(r"(?:taxable\s*value|sub\s*total|taxable\s*amount)\s*[:.\-]?\s*([0-9,]+\.?[0-9]*)", text, re.I)
        if taxable_match:
            goods_and_taxes["taxable_value"] = taxable_match.group(1).replace(",", "").strip()

        words_match = re.search(r"(?:amount\s*chargeable\s*\(in\s*words\)|in\s*words)\s*[:.\-]?\s*([^\n\r]+)", text, re.I)
        if words_match:
            goods_and_taxes["amount_in_words"] = words_match.group(1).strip()

        if goods_and_taxes:
            data["goods_and_tax_details"] = goods_and_taxes

        # 6. Terms and conditions
        terms = []
        lower_text = text.lower()
        t_pos = lower_text.find("terms and conditions")
        if t_pos == -1:
            t_pos = lower_text.find("terms & conditions")

        if t_pos != -1:
            snippet = text[t_pos:t_pos + 1500]
            for line in snippet.split("\n")[1:]:
                l_str = line.strip()
                if not l_str:
                    continue
                if any(w in l_str.lower() for w in ["declaration", "authorised signatory", "for "]):
                    break
                if re.match(r"^(\d+[\.\)]|•|-|\*)\s*", l_str):
                    terms.append(l_str)

        if terms:
            data["terms_and_conditions"] = terms

        return data

    def _extract_agreement_structure(self, text: str) -> Dict[str, Any]:
        data = {}
        lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("---")]
        if lines:
            data["agreement_title"] = lines[0]

        date_match = re.search(r"(?:dated|made\s+this|effective\s+date)\s+([A-Za-z0-9\s,\/\-]+)", text, re.I)
        if date_match:
            data["effective_date"] = date_match.group(1).strip()

        clauses = []
        for line in lines:
            if re.match(r"^(?:clause\s*\d+|section\s*\d+|\d+\.\s+[A-Z])", line, re.I):
                clauses.append(line)

        if clauses:
            data["clauses"] = clauses[:15]

        return data

    def _extract_bank_statement_structure(self, text: str, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        data = {}
        acc_match = re.search(r"(?:account\s*no|a\/c\s*no)\s*[:.\-]?\s*([0-9]{9,18})", text, re.I)
        if acc_match:
            data["account_number"] = acc_match.group(1).strip()

        period_match = re.search(r"(?:statement\s*period|period)\s*[:.\-]?\s*([A-Za-z0-9\s\/\-\.]+)", text, re.I)
        if period_match:
            data["statement_period"] = period_match.group(1).strip()

        if tables:
            data["transactions"] = tables[0].get("rows", [])

        return data

    def _extract_general_document_structure(self, text: str, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("---")]
        data = {
            "title": lines[0] if lines else "Document",
            "summary_content": text[:1000] if len(text) > 1000 else text
        }
        if tables:
            data["tables_extracted"] = tables
        return data

json_generator = DynamicJSONGenerator()
