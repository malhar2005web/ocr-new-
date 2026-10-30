from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional
from app.core.logging import logger

def to_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, Decimal):
        return val
    if isinstance(val, str):
        # Remove currency symbols and formatting commas
        cleaned = val.replace("₹", "").replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None

class IntegrityValidator:
    """
    Independent Python validation engine using Python Decimal for financial integrity.
    Never mutates extracted source values to force an equality.
    """
    def validate_document(self, doc_type: str, structured_json: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        if doc_type in ["tax_invoice", "purchase_order", "bill_receipt"]:
            issues.extend(self._validate_financial_math(structured_json))

        # Determine overall validation status
        if any(i["issue_type"] in ["arithmetic_mismatch", "tax_mismatch", "grand_total_mismatch"] for i in issues):
            status = "review_needed"
        elif issues:
            status = "review_needed"
        else:
            status = "valid"

        return {
            "status": status,
            "issues": issues,
            "confidence_score": 1.0 if not issues else 0.75
        }

    def _validate_financial_math(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        # Check goods and tax details or root items
        goods_sec = data.get("goods_and_tax_details") or data
        items = goods_sec.get("items") or data.get("items") or []

        calculated_subtotal = Decimal("0.00")
        has_items = False

        # 1. Validate line item calculations
        for idx, item in enumerate(items):
            qty = to_decimal(item.get("quantity"))
            rate = to_decimal(item.get("rate") or item.get("unit_price"))
            amount = to_decimal(item.get("amount") or item.get("total_amount"))
            discount = to_decimal(item.get("discount") or 0)

            if amount is not None:
                has_items = True
                calculated_subtotal += amount

            if qty is not None and rate is not None and amount is not None:
                expected_amount = (qty * rate) - (discount or Decimal("0"))
                # Allow minor fractional tolerance due to rounding
                diff = abs(expected_amount - amount)
                if diff > Decimal("0.05"):
                    issues.append({
                        "issue_type": "arithmetic_mismatch",
                        "field": f"items[{idx}].amount",
                        "message": (
                            f"Line item {idx+1} calculation mismatch: Quantity ({qty}) × Rate ({rate}) "
                            f"= {expected_amount:.2f}, but extracted amount is {amount:.2f}."
                        ),
                        "expected": float(expected_amount),
                        "actual": float(amount)
                    })

        # 2. Validate taxable value / subtotal sum
        reported_taxable = to_decimal(
            goods_sec.get("taxable_value")
            or goods_sec.get("subtotal")
            or data.get("taxable_value")
        )

        if has_items and reported_taxable is not None and len(items) > 1:
            diff = abs(calculated_subtotal - reported_taxable)
            if diff > Decimal("1.00"):
                issues.append({
                    "issue_type": "subtotal_sum_mismatch",
                    "field": "taxable_value",
                    "message": (
                        f"Sum of extracted line items ({calculated_subtotal:.2f}) does not match "
                        f"the reported taxable value ({reported_taxable:.2f})."
                    ),
                    "expected": float(calculated_subtotal),
                    "actual": float(reported_taxable)
                })

        # 3. Validate tax components
        tax_sec = goods_sec.get("tax_details") or goods_sec or data
        cgst = to_decimal(tax_sec.get("cgst_amount") or tax_sec.get("cgst"))
        sgst = to_decimal(tax_sec.get("sgst_amount") or tax_sec.get("sgst"))
        igst = to_decimal(tax_sec.get("igst_amount") or tax_sec.get("igst"))
        reported_total_tax = to_decimal(tax_sec.get("total_tax") or tax_sec.get("total_tax_amount"))

        calculated_tax = Decimal("0.00")
        tax_components_found = False
        for t in [cgst, sgst, igst]:
            if t is not None:
                calculated_tax += t
                tax_components_found = True

        if tax_components_found and reported_total_tax is not None:
            diff = abs(calculated_tax - reported_total_tax)
            if diff > Decimal("0.50"):
                issues.append({
                    "issue_type": "tax_mismatch",
                    "field": "tax_details.total_tax",
                    "message": (
                        f"Calculated sum of taxes (CGST + SGST + IGST = {calculated_tax:.2f}) "
                        f"does not match reported total tax ({reported_total_tax:.2f})."
                    ),
                    "expected": float(calculated_tax),
                    "actual": float(reported_total_tax)
                })

        # 4. Validate grand total
        grand_total = to_decimal(
            goods_sec.get("total_amount_after_tax")
            or goods_sec.get("grand_total")
            or data.get("grand_total")
        )

        effective_taxable = reported_taxable or (calculated_subtotal if has_items else None)
        effective_tax = reported_total_tax or (calculated_tax if tax_components_found else Decimal("0.00"))
        roundoff = to_decimal(goods_sec.get("round_off") or data.get("round_off") or Decimal("0.00"))

        if effective_taxable is not None and grand_total is not None:
            expected_grand = effective_taxable + effective_tax + (roundoff or Decimal("0.00"))
            diff = abs(expected_grand - grand_total)
            if diff > Decimal("2.00"):
                issues.append({
                    "issue_type": "grand_total_mismatch",
                    "field": "grand_total",
                    "message": (
                        f"Expected grand total (Taxable {effective_taxable:.2f} + Tax {effective_tax:.2f} "
                        f"+ Round-off = {expected_grand:.2f}) differs from extracted grand total ({grand_total:.2f})."
                    ),
                    "expected": float(expected_grand),
                    "actual": float(grand_total)
                })

        return issues

validator = IntegrityValidator()

