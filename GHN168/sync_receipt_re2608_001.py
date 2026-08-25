#!/usr/bin/env python3
"""
================================================================================
GHN168 - Sync Receipt RE2608-001 (บริษัท ไอเด็กซ์ ไมซ์ จำกัด - Tasty Singapore)
================================================================================
Author: Q (น้องคิว - Lead Backend Developer, ChZ Agent Corp)
Target: Google Sheets Tab 'รายรับ' (1 consolidated row with 24 columns)
================================================================================
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ghn168_sync_service import (
    format_branch_for_sheet,
    format_tax_id_for_sheet,
    sync_document_to_sheets,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncReceiptRE2608_001")

# ==============================================================================
# ข้อมูลใบเสร็จรับเงิน RE2608-001 (ไอเด็กซ์ ไมซ์ - Tasty Singapore)
# ==============================================================================
RECEIPT_RE2608_001_DATA: Dict[str, Any] = {
    "doc_date": "04/08/2026",
    "doc_no": "RE2608-001",
    "ref_invoice_no": "-",
    "client_name": "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
    "client_tax_id": "0505555007201",
    "client_address": "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
    "client_branch": "00000",
    "project_name": "Tasty singapore (ถ่ายทำวิดีโอ 3 คิว, ตัดต่อ 1 คลิป, เช่า GoPro 2 คิว, ชุดไฟ+ไมค์ไวเลส)",
    "pre_vat": 41000.0,
    "vat_amount": 2870.0,
    "gross_amount": 43870.0,
    "wht_rate": 3.0,
    "wht_amount": 1230.0,
    "net_total": 42640.0,
    "receiving_bank": "KTB",
    "payment_status": "ชำระเงินแล้ว",
    "actual_payment_date": "04/08/2026",
    "profit_share": "บริษัท (กองกลาง 100%)",
    "pdf_url": "https://drive.google.com/file/d/ghn168_receipt_re2608_001_idex/view",
    "recorded_by": "เลขาเฟิส (GHN168)",
    "remarks": "-",
    "discount": 0.0,
    "discount_desc": "-",
}


def build_receipt_row(doc_data: Dict[str, Any], record_date: Optional[str] = None) -> List[Any]:
    """
    Builds the 24-column row list matching GHN168 Google Sheets schema for tab 'รายรับ'.
    """
    now_str = record_date or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    tax_id_val = format_tax_id_for_sheet(doc_data.get("client_tax_id"))
    branch_val = format_branch_for_sheet(doc_data.get("client_branch"))

    row = [
        now_str,                                                    # 0: record_date
        doc_data.get("doc_date", "04/08/2026"),                     # 1: doc_date
        doc_data.get("doc_no", "RE2608-001"),                       # 2: doc_no
        doc_data.get("ref_invoice_no", "-"),                        # 3: ref_invoice_no
        doc_data.get("client_name", "บริษัท ไอเด็กซ์ ไมซ์ จำกัด"),  # 4: client_name
        tax_id_val,                                                 # 5: client_tax_id ('0505555007201')
        doc_data.get("client_address", "-"),                        # 6: client_address
        branch_val,                                                 # 7: client_branch ('00000')
        doc_data.get("project_name", "-"),                          # 8: project_name / detail
        float(doc_data.get("pre_vat", 0.0)),                        # 9: pre_vat
        float(doc_data.get("vat_amount", 0.0)),                     # 10: vat_amount
        float(doc_data.get("gross_amount", 0.0)),                   # 11: gross_amount
        float(doc_data.get("wht_rate", 0.0)),                       # 12: wht_rate
        float(doc_data.get("wht_amount", 0.0)),                     # 13: wht_amount
        float(doc_data.get("net_total", 0.0)),                      # 14: net_total
        doc_data.get("receiving_bank", "KTB"),                      # 15: receiving_bank
        doc_data.get("payment_status", "ชำระเงินแล้ว"),             # 16: payment_status
        doc_data.get("actual_payment_date", "04/08/2026"),          # 17: actual_payment_date
        doc_data.get("profit_share", "บริษัท (กองกลาง 100%)"),       # 18: profit_share
        doc_data.get("pdf_url", "-"),                               # 19: pdf_url
        doc_data.get("recorded_by", "เลขาเฟิส (GHN168)"),           # 20: recorded_by
        doc_data.get("remarks", "-"),                               # 21: remarks
        float(doc_data.get("discount", 0.0)),                       # 22: discount
        doc_data.get("discount_desc", "-")                          # 23: discount_desc
    ]
    return row


def sync_receipt_re2608_001() -> Dict[str, Any]:
    """
    Executes the sync of receipt RE2608-001 to Google Sheets tab 'รายรับ'.
    """
    print("=" * 80)
    print("🚀 GHN168 - SYNC RECEIPT RE2608-001 (IDEX MICE) TO GOOGLE SHEETS TAB 'รายรับ'")
    print(f"Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    # 1. Build row data
    row_data = build_receipt_row(RECEIPT_RE2608_001_DATA)
    print(f"\n📦 [1/2] Prepared 24-column row data:")
    for idx, val in enumerate(row_data):
        print(f"  Col {idx:02d}: {repr(val)}")

    assert len(row_data) == 24, f"Expected 24 columns, got {len(row_data)}"

    # 2. Call sync_document_to_sheets("รายรับ", values=row_data)
    print(f"\n📡 [2/2] Calling sync_document_to_sheets('รายรับ', values=row_data)...")
    sync_result = sync_document_to_sheets("รายรับ", values=row_data)
    print(f"  -> Sync Result: {json.dumps(sync_result, ensure_ascii=False, indent=2)}")

    print("\n" + "=" * 80)
    print("✅ RECEIPT RE2608-001 SYNC PROCESS COMPLETED")
    print(f"  • Doc No:        {RECEIPT_RE2608_001_DATA['doc_no']}")
    print(f"  • Client:        {RECEIPT_RE2608_001_DATA['client_name']}")
    print(f"  • Tax ID:        {row_data[5]}")
    print(f"  • Branch:        {row_data[7]}")
    print(f"  • Pre-VAT:       {RECEIPT_RE2608_001_DATA['pre_vat']:,.2f} ฿")
    print(f"  • VAT 7%:        {RECEIPT_RE2608_001_DATA['vat_amount']:,.2f} ฿")
    print(f"  • Gross Amount:  {RECEIPT_RE2608_001_DATA['gross_amount']:,.2f} ฿")
    print(f"  • WHT 3%:        {RECEIPT_RE2608_001_DATA['wht_amount']:,.2f} ฿")
    print(f"  • Net Received:  {RECEIPT_RE2608_001_DATA['net_total']:,.2f} ฿")
    print(f"  • Bank:          {RECEIPT_RE2608_001_DATA['receiving_bank']}")
    print(f"  • Status:        {RECEIPT_RE2608_001_DATA['payment_status']}")
    print(f"  • Sync Status:   {sync_result.get('status', 'synced')}")
    print("=" * 80)

    return {
        "row_data": row_data,
        "sync_result": sync_result
    }


if __name__ == "__main__":
    sync_receipt_re2608_001()
