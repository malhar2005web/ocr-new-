import json
import re
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.llm_verifier import llm_verifier
from app.services.json_generator import clean_dynamic_json

def _parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.-]", "", val.replace(",", "").strip())
        try:
            return float(cleaned)
        except Exception:
            return None
    return None

class PolishedJSONService:
    """
    Transforms universal/raw extracted document JSON into the standardized
    Purchase Books & ERP Accounting format with AI semantic field matching
    and deterministic zero-fail fallback.
    """

    def generate_polished_json(self, universal_json: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        if not universal_json:
            return {}

        # Attempt AI Semantic Polishing via Gemini
        if llm_verifier.is_available():
            try:
                ai_result = self._generate_with_ai(universal_json, raw_text)
                if ai_result and isinstance(ai_result, dict) and len(ai_result) > 2:
                    return clean_dynamic_json(ai_result)
            except Exception as e:
                logger.warning(f"AI Polished JSON generation skipped/failed ({e}). Using deterministic mapper.")

        # Fallback to Deterministic Mapping
        return self._generate_deterministic(universal_json, raw_text)

    def _generate_with_ai(self, universal_json: Dict[str, Any], raw_text: str = "") -> Optional[Dict[str, Any]]:
        system_prompt = (
            "You are an expert ERP & Accounting Data Architect. "
            "Your task is to transform the provided extracted document JSON into a standardized "
            "Purchase Book / Accounting JSON structure.\n\n"
            "TARGET SCHEMA:\n"
            "{\n"
            '  "GRN_No_Bill_No_Voucher_No": "<Invoice / Bill / GRN / Voucher Number>",\n'
            '  "Bill_Date": "<Document Date e.g. DD/MM/YYYY>",\n'
            '  "Supplier": {\n'
            '    "name": "<Supplier / Seller Company Name>",\n'
            '    "address": "<Supplier Address>",\n'
            '    "gstin": "<Supplier GSTIN>",\n'
            '    "pan": "<Supplier PAN>"\n'
            '  },\n'
            '  "Products": [\n'
            '    {\n'
            '      "SrNo": 1,\n'
            '      "Product": "<Product or Item Description>",\n'
            '      "Product_Details": "<Combined details e.g. HSN 520811, Lot No. 547, Bale No. B-701>",\n'
            '      "Value_Rate_Product_Amount": {\n'
            '        "rate": <unit rate as number>,\n'
            '        "amount": <line item amount as number>\n'
            '      },\n'
            '      "Pcs_Qty": {\n'
            '        "pcs": <pcs or bales as number>,\n'
            '        "quantity": <item quantity as number>,\n'
            '        "unit": "<MTR. / KGS / PCS / NOS etc.>"\n'
            '      }\n'
            '    }\n'
            '  ],\n'
            '  "Other_Information_Remark_Narration_Description_TNC": {\n'
            '    "discount": <discount amount as number if present>,\n'
            '    "buyer": "<Buyer / Billed To Name>",\n'
            '    "buyer_gstin": "<Buyer GSTIN>",\n'
            '    "bank_details": {\n'
            '      "bank_name": "<Bank Name>",\n'
            '      "branch": "<Branch Name>",\n'
            '      "account_number": "<Account Number>",\n'
            '      "ifsc": "<IFSC Code>"\n'
            '    },\n'
            '    "remarks": "<Any remarks / narrations / terms>"\n'
            '  },\n'
            '  "Location_Address": {\n'
            '    "name": "<Consignee / Shipped To / Delivery Site Name>",\n'
            '    "address": "<Consignee / Delivery Address>",\n'
            '    "gstin": "<Consignee GSTIN>"\n'
            '  },\n'
            '  "TaxAmt_Tax_Taxable_Amount": {\n'
            '    "taxable_amount": <taxable amount as number>,\n'
            '    "cgst": <CGST amount as number>,\n'
            '    "sgst": <SGST amount as number>,\n'
            '    "igst": <IGST amount as number>,\n'
            '    "total_tax": <total tax as number>\n'
            '  },\n'
            '  "Invoice_Amount": <Grand total / Total payable amount as number>,\n'
            '  "Total_Qty": <Total quantity as number>,\n'
            '  "Total_Pcs": <Total pieces as number>\n'
            "}\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY valid parseable JSON matching the target schema.\n"
            "2. Map similar fields intelligently: e.g. Consignee / Ship-To / Site address maps to 'Location_Address'.\n"
            "3. Omit null or empty fields if not present in the input.\n"
            "4. Convert numeric values to numbers (float/int) where appropriate.\n"
            "5. Do not invent any numbers, names or codes."
        )

        user_content = (
            f"INPUT EXTRACTED JSON:\n{json.dumps(universal_json, indent=2)}\n\n"
        )
        if raw_text:
            user_content += f"RAW DOCUMENT EXCERPT:\n{raw_text[:8000]}\n\n"

        user_content += "Produce the Polished JSON strictly following the target accounting schema."

        models_to_try = [settings.LLM_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        seen_models = []
        for m in models_to_try:
            if m not in seen_models:
                seen_models.append(m)

        for model_name in seen_models:
            try:
                response = llm_verifier.client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config={
                        "system_instruction": system_prompt,
                        "response_mime_type": "application/json"
                    }
                )
                if response and response.text:
                    cleaned_str = response.text.strip()
                    cleaned_str = re.sub(r"^```(?:json)?\s*", "", cleaned_str)
                    cleaned_str = re.sub(r"\s*```$", "", cleaned_str)
                    parsed = json.loads(cleaned_str)
                    return parsed
            except Exception as e:
                logger.warning(f"Polished JSON AI call failed on model {model_name}: {e}")
                continue

        return None

    def _generate_deterministic(self, u: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        """
        Robust deterministic mapper guaranteeing 100% availability of the Polished JSON structure.
        """
        # 1. Invoice / Bill Number
        bill_no = (
            u.get("invoice_number")
            or u.get("invoice_no")
            or u.get("bill_no")
            or u.get("grn_no")
            or u.get("voucher_no")
            or u.get("challan_no")
            or u.get("document_id")
        )
        if not bill_no and raw_text:
            m = re.search(r"\b(?:invoice\s*no\.?|bill\s*no\.?|challan\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", raw_text, re.IGNORECASE)
            if m:
                bill_no = m.group(1).strip()

        # 2. Bill Date
        bill_date = (
            u.get("invoice_date")
            or u.get("date")
            or u.get("bill_date")
            or u.get("dated")
        )
        if not bill_date and raw_text:
            m = re.search(r"\b(?:date|dated)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", raw_text, re.IGNORECASE)
            if m:
                bill_date = m.group(1).strip()

        # 3. Supplier / Seller
        supplier_raw = u.get("supplier") or u.get("seller") or u.get("vendor") or {}
        supplier_obj = {}
        if isinstance(supplier_raw, dict):
            for k in ["name", "address", "gstin", "pan"]:
                if supplier_raw.get(k):
                    supplier_obj[k] = supplier_raw[k]
        elif isinstance(supplier_raw, str):
            supplier_obj["name"] = supplier_raw

        # 4. Products / Items
        raw_items = (
            u.get("line_items")
            or u.get("items")
            or u.get("goods_and_tax_details", {}).get("items")
            or []
        )
        products = []
        tot_qty = 0.0
        tot_pcs = 0

        for idx, itm in enumerate(raw_items, start=1):
            if not isinstance(itm, dict):
                continue
            sr = itm.get("sr_no") or itm.get("serial_number") or idx
            prod_name = itm.get("product_name") or itm.get("product_description") or itm.get("description") or "Item"
            
            # Details: HSN, Lot No, Bale No
            details_parts = []
            if itm.get("hsn_code") or itm.get("hsn"):
                details_parts.append(f"HSN {itm.get('hsn_code') or itm.get('hsn')}")
            if itm.get("lot_no"):
                details_parts.append(f"Lot No. {itm.get('lot_no')}")
            if itm.get("bale_no") or itm.get("bale"):
                details_parts.append(f"Bale {itm.get('bale_no') or itm.get('bale')}")
            details_str = ", ".join(details_parts) if details_parts else None

            # Rate & Amount
            rate_val = _parse_float(itm.get("rate_per_unit") or itm.get("rate"))
            amt_val = _parse_float(itm.get("amount") or itm.get("value") or itm.get("total"))
            val_rate = {}
            if rate_val is not None:
                val_rate["rate"] = rate_val
            if amt_val is not None:
                val_rate["amount"] = amt_val

            # Pcs & Quantity
            qty_val = _parse_float(itm.get("quantity") or itm.get("qty"))
            pcs_val = None
            raw_pcs = itm.get("pieces") or itm.get("pcs") or itm.get("bale_no")
            if raw_pcs is not None:
                try:
                    pcs_val = int(float(str(raw_pcs).replace(",", "")))
                except Exception:
                    pass

            if qty_val:
                tot_qty += qty_val
            if pcs_val:
                tot_pcs += pcs_val

            pcs_qty = {}
            if pcs_val is not None:
                pcs_qty["pcs"] = pcs_val
            if qty_val is not None:
                pcs_qty["quantity"] = qty_val
            if itm.get("unit"):
                pcs_qty["unit"] = itm.get("unit")

            p_entry = {"SrNo": int(sr) if str(sr).isdigit() else sr, "Product": prod_name}
            if details_str:
                p_entry["Product_Details"] = details_str
            if val_rate:
                p_entry["Value_Rate_Product_Amount"] = val_rate
            if pcs_qty:
                p_entry["Pcs_Qty"] = pcs_qty

            products.append(p_entry)

        # 5. Other Information / Remark / Narration / Description / TNC
        other_info = {}
        disc_val = _parse_float(u.get("discount") or u.get("trade_discount"))
        if disc_val is not None:
            other_info["discount"] = disc_val

        buyer_raw = u.get("buyer") or u.get("customer") or {}
        if isinstance(buyer_raw, dict):
            if buyer_raw.get("name"):
                other_info["buyer"] = buyer_raw["name"]
            if buyer_raw.get("gstin"):
                other_info["buyer_gstin"] = buyer_raw["gstin"]
        elif isinstance(buyer_raw, str):
            other_info["buyer"] = buyer_raw

        bank_raw = u.get("bank_details") or {}
        if isinstance(bank_raw, dict) and bank_raw:
            other_info["bank_details"] = bank_raw

        if u.get("remarks") or u.get("narration"):
            other_info["remarks"] = u.get("remarks") or u.get("narration")
        if u.get("terms_and_conditions"):
            other_info["terms_and_conditions"] = u["terms_and_conditions"]

        # 6. Location Address (Consignee / Shipped To / Delivery Site)
        consignee_raw = u.get("consignee") or u.get("shipped_to") or u.get("delivery_address") or {}
        location_obj = {}
        if isinstance(consignee_raw, dict):
            for k in ["name", "address", "gstin"]:
                if consignee_raw.get(k):
                    location_obj[k] = consignee_raw[k]
        elif isinstance(consignee_raw, str):
            location_obj["name"] = consignee_raw

        # 7. TaxAmt / Tax / Taxable Amount
        tax_obj = {}
        taxable_val = _parse_float(u.get("taxable_value") or u.get("taxable_amount") or u.get("subtotal"))
        cgst_val = _parse_float(u.get("cgst_amount") or u.get("cgst"))
        sgst_val = _parse_float(u.get("sgst_amount") or u.get("sgst"))
        igst_val = _parse_float(u.get("igst_amount") or u.get("igst"))
        total_tax_val = _parse_float(u.get("total_gst") or u.get("total_tax"))

        if taxable_val is not None:
            tax_obj["taxable_amount"] = taxable_val
        if cgst_val is not None:
            tax_obj["cgst"] = cgst_val
        if sgst_val is not None:
            tax_obj["sgst"] = sgst_val
        if igst_val is not None:
            tax_obj["igst"] = igst_val
        if total_tax_val is not None:
            tax_obj["total_tax"] = total_tax_val
        elif cgst_val is not None and sgst_val is not None:
            tax_obj["total_tax"] = round(cgst_val + sgst_val + (igst_val or 0.0), 2)

        # 8. Invoice Amount
        inv_amt = _parse_float(
            u.get("grand_total")
            or u.get("total_payable_amount")
            or u.get("invoice_amount")
            or u.get("total_amount")
        )

        # Assemble Polished JSON
        result = {}
        if bill_no:
            result["GRN_No_Bill_No_Voucher_No"] = str(bill_no)
        if bill_date:
            result["Bill_Date"] = str(bill_date)
        if supplier_obj:
            result["Supplier"] = supplier_obj
        if products:
            result["Products"] = products
        if other_info:
            result["Other_Information_Remark_Narration_Description_TNC"] = other_info
        if location_obj:
            result["Location_Address"] = location_obj
        if tax_obj:
            result["TaxAmt_Tax_Taxable_Amount"] = tax_obj
        if inv_amt is not None:
            result["Invoice_Amount"] = inv_amt

        # Totals
        printed_qty = _parse_float(u.get("total_quantity") or u.get("total_qty"))
        printed_pcs = _parse_float(u.get("total_pieces") or u.get("total_pcs"))
        
        final_qty = printed_qty if printed_qty is not None else (round(tot_qty, 2) if tot_qty > 0 else None)
        final_pcs = int(printed_pcs) if printed_pcs is not None else (tot_pcs if tot_pcs > 0 else None)

        if final_qty is not None:
            result["Total_Qty"] = final_qty
        if final_pcs is not None:
            result["Total_Pcs"] = final_pcs

        return clean_dynamic_json(result)

polished_json_service = PolishedJSONService()
