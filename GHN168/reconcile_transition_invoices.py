#!/usr/bin/env python3
"""
Reconcile and clear 6 transition invoices in Google Sheets tabs 'ใบวางบิล' and 'รายรับ'.
"""

import logging
from ghn168_sync_service import (
    read_sheet_data,
    overwrite_sheet_data,
    INVOICE_HEADERS,
    INCOME_HEADERS,
    get_overdue_and_aging_invoices,
    normalize_doc_no,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_invoices")


def reconcile():
    # -------------------------------------------------------------------------
    # 1. Update 'ใบวางบิล' (Invoices)
    # -------------------------------------------------------------------------
    logger.info("Reading live 'ใบวางบิล' tab...")
    billing_res = read_sheet_data("ใบวางบิล")
    billing_rows = [list(r) for r in billing_res.get("values", [])]
    
    # Pad rows to length of INVOICE_HEADERS if needed
    for r in billing_rows:
        while len(r) < len(INVOICE_HEADERS):
            r.append("")

    billing_remarks_map = {
        "IV2608-001": "ชำระแล้ว (โอนเข้า ธ.กรุงไทย ยอด 53,500.00 บาท)",
        "IV-608001": "ชำระแล้ว (โอนเข้า ธ.กรุงไทย ยอด 53,500.00 บาท)",
        "IV2607-002": "ชำระแล้ว (อ้างอิง RE2608-001 ยอด 42,640.00 บาท)",
        "IV2607-002-LANNA": "ชำระแล้ว (โอนเข้า ธ.กรุงไทย ยอด 31,200.00 บาท)",
        "IV2608-001-NORTH": "ชำระแล้ว (โอนเข้า ธ.กรุงไทย ยอด 52,000.00 บาท)",
        "IV2608-003": "ชำระแล้ว (แบ่งชำระ 2 งวด: หอม-RE2607-001 ยอด 15,600 + 16,640 บาท)",
        "IV2608-004": "ชำระแล้ว (ส่งแมสเซนเจอร์รับเช็คและขึ้นเงินเรียบร้อย ยอด 83,200.00 บาท)",
        "IV2607-001": "ชำระแล้ว (อ้างอิง RE2608-002 ยอด 2,080.00 บาท)",
        "เก่ง-IV2606-001": "ชำระแล้ว (อ้างอิง เก่ง-RE2606-002 ยอด 10,400.00 บาท)",
        "IV-202608-586": "ชำระแล้ว (อ้างอิง RE-202608-586)",
    }

    updated_billing_count = 0
    for r in billing_rows:
        doc_no = str(r[2]).strip()
        norm_doc = normalize_doc_no(doc_no)
        # Check matching (longest key first to avoid prefix shadowing)
        matched_remark = None
        for k in sorted(billing_remarks_map.keys(), key=len, reverse=True):
            v = billing_remarks_map[k]
            if doc_no == k or norm_doc == normalize_doc_no(k) or (len(k) >= 10 and k.lower() in doc_no.lower()):
                matched_remark = v
                break
        
        if matched_remark:
            r[22] = matched_remark  # Column 23 (Index 22): หมายเหตุ (Remarks)
            logger.info("Updated billing row %s -> %s", doc_no, matched_remark)
            updated_billing_count += 1

    logger.info("Overwriting 'ใบวางบิล' with %d updated rows...", len(billing_rows))
    res_b = overwrite_sheet_data("ใบวางบิล", INVOICE_HEADERS, billing_rows)
    logger.info("Overwrote 'ใบวางบิล': %s", res_b.get("status"))

    # -------------------------------------------------------------------------
    # 2. Update 'รายรับ' (Receipts)
    # -------------------------------------------------------------------------
    logger.info("Reading live 'รายรับ' tab...")
    receipt_res = read_sheet_data("รายรับ")
    receipt_rows = [list(r) for r in receipt_res.get("values", [])]

    for r in receipt_rows:
        while len(r) < len(INCOME_HEADERS):
            r.append("")

    # Map receipt rows to ref_invoice_no
    # Column D (index 3) is ref_invoice_no
    for idx, r in enumerate(receipt_rows):
        doc_no = str(r[2]).strip()
        desc = str(r[8]).strip() if len(r) > 8 else ""

        if "RE2608-001" in doc_no and "Tasty Singapore" in desc:
            r[3] = "IV2607-002"
            logger.info("Row %d (%s) ref set to IV2607-002", idx, doc_no)
        elif "RE2607-001" in doc_no and "งวด 1" in desc:
            r[3] = "IV2608-003"
            logger.info("Row %d (%s, งวด 1) ref set to IV2608-003", idx, doc_no)
        elif "RE2607-001" in doc_no and "งวด 2" in desc:
            r[3] = "IV2608-003"
            logger.info("Row %d (%s, งวด 2) ref set to IV2608-003", idx, doc_no)
        elif "RE2608-002" in doc_no:
            r[3] = "IV2607-001"
            logger.info("Row %d (%s) ref set to IV2607-001", idx, doc_no)

    logger.info("Overwriting 'รายรับ' with %d updated rows...", len(receipt_rows))
    res_r = overwrite_sheet_data("รายรับ", INCOME_HEADERS, receipt_rows)
    logger.info("Overwrote 'รายรับ': %s", res_r.get("status"))

    # -------------------------------------------------------------------------
    # 3. Verification
    # -------------------------------------------------------------------------
    logger.info("Verifying overdue and aging invoices...")
    overdue_data = get_overdue_and_aging_invoices()
    total_overdue_invoices = overdue_data.get("total_overdue_invoices")
    total_overdue_amount = overdue_data.get("total_overdue_amount")
    total_overdue_count = overdue_data.get("total_overdue_count")

    logger.info("Verification results:")
    logger.info("  total_overdue_invoices: %s", total_overdue_invoices)
    logger.info("  total_overdue_count: %s", total_overdue_count)
    logger.info("  total_overdue_amount: %.2f ฿", total_overdue_amount)

    assert total_overdue_invoices == 0, f"Expected 0 overdue invoices, got {total_overdue_invoices}"
    assert total_overdue_amount == 0.0, f"Expected 0.00 overdue amount, got {total_overdue_amount}"
    logger.info("Reconciliation and verification completed successfully!")


if __name__ == "__main__":
    reconcile()
