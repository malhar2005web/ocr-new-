import json
import re
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.services.llm_verifier import llm_verifier

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

def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()

class PolishedJSONService:
    """
    Transforms universal extracted document JSON into the exact
    Purchase Books accounting schema requested by the user,
    with identical field names and spacing.
    """

    def generate_polished_json(self, universal_json: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
        if not universal_json:
            return {}

        # 1. Attempt AI Semantic Polishing via Gemini
        if llm_verifier.is_available():
            try:
                ai_result = self._generate_with_ai(universal_json, raw_text)
                if ai_result and isinstance(ai_result, dict):
                    # Check if 'Purchase Books' key is present or root keys
                    if "Purchase Books" in ai_result and isinstance(ai_result["Purchase Books"], dict):
                        return ai_result
                    elif "Bill No" in ai_result or "Supplier" in ai_result:
                        return {"Purchase Books": ai_result}
            except Exception as e:
                logger.warning(f"AI Polished JSON generation skipped/failed ({e}). Using deterministic mapper.")

        # 2. Fallback to Deterministic Mapping
        return self._generate_deterministic(universal_json, raw_text)

    def _generate_with_ai(self, universal_json: Dict[str, Any], raw_text: str = "") -> Optional[Dict[str, Any]]:
        system_prompt = (
            "You are an expert ERP & Accounting Data Architect.\n"
            "Your task is to transform the provided extracted document data into the EXACT Purchase Books accounting schema below.\n\n"
            "CRITICAL: USE THE EXACT FIELD NAMES AND EXACT SPACING SHOWN BELOW. DO NOT ALTER OR RENAME ANY KEYS.\n\n"
            "TARGET SCHEMA:\n"
            "{\n"
            '  "Purchase Books": {\n'
            '    "GRN No.": "<GRN number if printed, else empty string \"\">",\n'
            '    "Voucher No": "<Voucher or Invoice Number e.g. MT/1520>",\n'
            '    "Voucher Date  :": "<Voucher date or Invoice date e.g. 14-Dec-21>",\n'
            '    "Supplier": "<Supplier / Seller Company Name as string>",\n'
            '    "Bill No": "<Vendor Bill Number / Invoice Number e.g. MT/1520>",\n'
            '    "Bill Date  ": "<Vendor Bill Date e.g. 14-Dec-21>",\n'
            '    "Product Amount": <total assessable / line item product value as number>,\n'
            '    "Taxable Amount": <taxable amount as number>,\n'
            '    "Total Qty": <total quantity as number>,\n'
            '    "Total Pcs": <total pieces / bales as number>,\n'
            '    "total Tax": <total tax amount as number>,\n'
            '    "Invoice Amount": <grand total / invoice payable amount as number>,\n'
            '    "Narration": "<narration, remarks or payment notes from the invoice>",\n'
            '    "Product Details": [\n'
            "      {\n"
            '        "SrNo": 1,\n'
            '        "Product": "<Full product description>",\n'
            '        "Qty": <item quantity as number>,\n'
            '        "Rate": <item rate as number>,\n'
            '        "Value": <item amount / value as number>,\n'
            '        "Pcs": <item pieces / bales as number>,\n'
            '        "Quality": "<quality name / construction e.g. Rudraksh 52*50-47>",\n'
            '        "Other Information": "<bale numbers or lot number e.g. BALE NO 394 TO 400>",\n'
            '        "Location": "<delivery site or consignee location address>",\n'
            '        "Remark": "<item remark e.g. BALE[7}>",\n'
            '        "Chapter Heading": "<HSN code or chapter heading e.g. 5208>"\n'
            "      }\n"
            "    ],\n"
            '    "Terms": "<terms and conditions, interest, due date text>",\n'
            '    "cgst": <CGST amount as number>,\n'
            '    "sgst": <SGST amount as number>\n'
            "  }\n"
            "}\n\n"
            "RULES:\n"
            "1. Output ONLY valid parseable JSON matching the exact schema above.\n"
            "2. Note the EXACT SPACING: 'Voucher Date  :' has 2 spaces before colon, 'Bill Date  ' has 2 spaces after Date, 'total Tax' has lowercase 't'.\n"
            "3. Do not invent any fake numbers or names. Extract accurately from source."
        )

        user_content = (
            f"INPUT EXTRACTED JSON:\n{json.dumps(universal_json, indent=2)}\n\n"
        )
        if raw_text:
            user_content += f"RAW DOCUMENT EXCERPT:\n{raw_text[:8000]}\n\n"

        user_content += "Produce the Purchase Books JSON strictly following the target schema."

        models_to_try = [settings.LLM_MODEL]
        seen_models = [settings.LLM_MODEL]

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
        Deterministic mapper producing the EXACT Purchase Books schema with identical field names and spacing.
        """
        # Bill / Invoice Number
        bill_no = _clean_str(
            u.get("invoice_number")
            or u.get("invoice_no")
            or u.get("bill_no")
            or u.get("voucher_no")
            or u.get("GRN_No_Bill_No_Voucher_No")
            or u.get("challan_no")
        )
        if not bill_no and raw_text:
            m = re.search(r"\b(?:invoice\s*no\.?|bill\s*no\.?|voucher\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-]+)", raw_text, re.IGNORECASE)
            if m:
                bill_no = m.group(1).strip()

        # Bill Date
        bill_date = _clean_str(
            u.get("invoice_date")
            or u.get("bill_date")
            or u.get("Bill_Date")
            or u.get("date")
            or u.get("dated")
        )
        if not bill_date and raw_text:
            m = re.search(r"\b(?:date|dated)\s*[:\-]?\s*(\d{1,2}[\/\-\.][A-Za-z0-9]+[\/\-\.]\d{2,4})", raw_text, re.IGNORECASE)
            if m:
                bill_date = m.group(1).strip()

        # Supplier Name
        supplier_val = u.get("supplier") or u.get("Supplier") or u.get("seller") or u.get("vendor") or ""
        if isinstance(supplier_val, dict):
            supplier_name = _clean_str(supplier_val.get("name") or supplier_val.get("supplier_name") or "")
        else:
            supplier_name = _clean_str(supplier_val)
        if not supplier_name and raw_text:
            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
            for ln in lines[:6]:
                if any(kw in ln.lower() for kw in ["textile", "mills", "solutions", "traders", "enterprises", "company", "ltd", "llp"]):
                    supplier_name = ln
                    break

        # Location Address (Consignee / Delivery site)
        loc_val = u.get("consignee") or u.get("Location_Address") or u.get("shipped_to") or {}
        location_str = ""
        if isinstance(loc_val, dict):
            parts = [loc_val.get("name"), loc_val.get("address")]
            location_str = ", ".join([p.strip() for p in parts if p and str(p).strip()])
        elif isinstance(loc_val, str):
            location_str = loc_val.strip()

        # Products list
        raw_items = (
            u.get("Product Details")
            or u.get("Products")
            or u.get("line_items")
            or u.get("items")
            or u.get("goods_and_tax_details", {}).get("items")
            or []
        )
        products_list: List[Dict[str, Any]] = []
        tot_qty = 0.0
        tot_pcs = 0
        tot_val = 0.0

        for idx, itm in enumerate(raw_items, start=1):
            if not isinstance(itm, dict):
                continue
            sr = itm.get("SrNo") or itm.get("sr_no") or itm.get("serial_number") or idx
            prod_name = _clean_str(itm.get("Product") or itm.get("product_name") or itm.get("product_description") or itm.get("description") or "Goods")
            
            # Rate & Value / Amount
            val_rate = itm.get("Value_Rate_Product_Amount") or {}
            rate_val = _parse_float(itm.get("Rate") or itm.get("rate") or val_rate.get("rate") or itm.get("rate_per_unit"))
            amt_val = _parse_float(itm.get("Value") or itm.get("amount") or itm.get("value") or val_rate.get("amount"))

            # Qty & Pcs
            pcs_qty = itm.get("Pcs_Qty") or {}
            qty_val = _parse_float(itm.get("Qty") or itm.get("quantity") or itm.get("qty") or pcs_qty.get("quantity"))
            pcs_val = None
            raw_pcs = itm.get("Pcs") or itm.get("pcs") or itm.get("pieces") or pcs_qty.get("pcs")
            if raw_pcs is not None:
                try:
                    pcs_val = int(float(str(raw_pcs).replace(",", "")))
                except Exception:
                    pass

            if qty_val is not None:
                tot_qty += qty_val
            if pcs_val is not None:
                tot_pcs += pcs_val
            if amt_val is not None:
                tot_val += amt_val

            # Quality
            quality_val = _clean_str(itm.get("Quality"))
            if not quality_val:
                m_q = re.search(r"\b([A-Za-z0-9\-]+(?:\s*\d+[\*x]\d+[\*x\-]?\d*))\b", prod_name)
                if m_q:
                    quality_val = m_q.group(1).strip()
                elif " - " in prod_name:
                    quality_val = prod_name.split(" - ")[0].strip()

            # Other Information (Bale no, lot no)
            other_info_val = _clean_str(itm.get("Other Information") or itm.get("Other_Information"))
            if not other_info_val:
                parts = []
                if itm.get("lot_no"):
                    parts.append(f"Lot No. {itm.get('lot_no')}")
                if itm.get("bale_no"):
                    parts.append(f"Bale No. {itm.get('bale_no')}")
                m_bale = re.search(r"\b(BALE\s*NO[^\(\{\[]+)", prod_name, re.IGNORECASE)
                if m_bale:
                    parts.append(m_bale.group(1).strip())
                other_info_val = ", ".join(parts)

            # Location
            item_loc = _clean_str(itm.get("Location")) or location_str

            # Remark
            remark_val = _clean_str(itm.get("Remark"))
            if not remark_val:
                m_rem = re.search(r"(\bBALE\s*\[\s*\d+\s*\}|\bBALE\s*\[\s*\d+\s*\])", prod_name, re.IGNORECASE)
                if m_rem:
                    remark_val = m_rem.group(1).strip()

            # Chapter Heading (HSN)
            chap_heading = _clean_str(itm.get("Chapter Heading") or itm.get("hsn_code") or itm.get("hsn") or itm.get("Product_Details"))
            if chap_heading:
                m_hsn = re.search(r"\b(?:HSN\s*)?(\d{4,8})\b", chap_heading, re.IGNORECASE)
                if m_hsn:
                    chap_heading = m_hsn.group(1)

            p_entry = {
                "SrNo": int(sr) if str(sr).isdigit() else sr,
                "Product": prod_name,
                "Qty": qty_val if qty_val is not None else 0.0,
                "Rate": rate_val if rate_val is not None else 0.0,
                "Value": amt_val if amt_val is not None else 0.0,
                "Pcs": pcs_val if pcs_val is not None else 0,
                "Quality": quality_val,
                "Other Information": other_info_val,
                "Location": item_loc,
                "Remark": remark_val,
                "Chapter Heading": chap_heading
            }
            products_list.append(p_entry)

        # Taxable Amount & Product Amount
        tax_wrap = u.get("TaxAmt_Tax_Taxable_Amount") or {}
        taxable_amt = _parse_float(
            u.get("Taxable Amount")
            or u.get("taxable_value")
            or u.get("taxable_amount")
            or tax_wrap.get("taxable_amount")
            or tot_val
        )
        prod_amt = _parse_float(u.get("Product Amount") or tot_val or taxable_amt)

        # Taxes: cgst, sgst, total Tax
        cgst_val = _parse_float(u.get("cgst") or u.get("cgst_amount") or tax_wrap.get("cgst"))
        sgst_val = _parse_float(u.get("sgst") or u.get("sgst_amount") or tax_wrap.get("sgst"))
        total_tax_val = _parse_float(u.get("total Tax") or u.get("total_tax") or u.get("total_gst") or tax_wrap.get("total_tax"))
        if total_tax_val is None and cgst_val is not None and sgst_val is not None:
            total_tax_val = round(cgst_val + sgst_val, 2)

        # Totals
        inv_amt = _parse_float(
            u.get("Invoice Amount")
            or u.get("Invoice_Amount")
            or u.get("grand_total")
            or u.get("total_payable_amount")
        )
        final_qty = _parse_float(u.get("Total Qty") or u.get("Total_Qty") or (tot_qty if tot_qty > 0 else None))
        final_pcs = _parse_float(u.get("Total Pcs") or u.get("Total_Pcs") or (tot_pcs if tot_pcs > 0 else None))

        # Narration & Terms
        other_wrap = u.get("Other_Information_Remark_Narration_Description_TNC") or {}
        narration_val = _clean_str(
            u.get("Narration")
            or u.get("narration")
            or other_wrap.get("remarks")
            or u.get("remarks")
        )
        terms_val = _clean_str(
            u.get("Terms")
            or u.get("terms")
            or other_wrap.get("terms_and_conditions")
            or u.get("terms_and_conditions")
            or narration_val
        )

        purchase_book_data = {
            "GRN No.": _clean_str(u.get("GRN No.") or u.get("grn_no") or ""),
            "Voucher No": bill_no,
            "Voucher Date  :": bill_date,
            "Supplier": supplier_name,
            "Bill No": bill_no,
            "Bill Date  ": bill_date,
            "Product Amount": prod_amt if prod_amt is not None else 0.0,
            "Taxable Amount": taxable_amt if taxable_amt is not None else 0.0,
            "Total Qty": final_qty if final_qty is not None else 0.0,
            "Total Pcs": int(final_pcs) if final_pcs is not None else 0,
            "total Tax": total_tax_val if total_tax_val is not None else 0.0,
            "Invoice Amount": inv_amt if inv_amt is not None else 0.0,
            "Narration": narration_val,
            "Product Details": products_list,
            "Terms": terms_val,
            "cgst": cgst_val if cgst_val is not None else 0.0,
            "sgst": sgst_val if sgst_val is not None else 0.0
        }

        return {"Purchase Books": purchase_book_data}

polished_json_service = PolishedJSONService()
