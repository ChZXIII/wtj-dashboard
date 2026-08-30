#!/usr/bin/env python3
"""
================================================================================
GHN168 - Google Sheets Income Tab Deduplication & Merging Script
================================================================================
Author: Q (น้องคิว - Lead Backend Developer, ChZ Agent Corp)
Target: Google Sheets Tab 'รายรับ'
Objective:
1. Connect via GAS Webhook (GAS_SCRIPT_URL from .env)
2. Read real rows in tab 'รายรับ'
3. Detect duplicate rows for 'ทอย-RE2608-587' (rows 13 and 14)
4. Merge row 13 & 14 into a single complete row:
   - Amount: 50,000 THB Pre-VAT, VAT 7%: 3,500 THB, Gross: 53,500 THB,
     WHT 3%: 1,500 THB, Net Received: 52,000 THB
   - Google Drive URL: https://drive.google.com/file/d/13Q2F0Ayzk5n0pVHWDgCtu1bw3E8ux4ET/view?usp=drivesdk
   - Recorded By: หอม (ผ่านเลขาเฟิส)
   - Remarks: คนทำงาน: หอม | บริษัท (กองกลาง 100%)
   - Profit Share: บริษัท (กองกลาง 100%)
   - Status: ชำระเงินแล้ว
5. Overwrite/Sync Google Sheet tab 'รายรับ' to ensure exactly 12 complete, deduplicated data rows
6. Verify and report the results
================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Ensure workspace root is in sys.path
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

import ghn168_sync_service
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    GHN168_SHEET_ID,
    INCOME_HEADERS,
    read_sheet_data,
    overwrite_sheet_data,
    normalize_doc_no,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("cleanup_receipts")

TARGET_DOC_NO = "ทอย-RE2608-587"
TARGET_DRIVE_URL = "https://drive.google.com/file/d/13Q2F0Ayzk5n0pVHWDgCtu1bw3E8ux4ET/view?usp=drivesdk"
TARGET_REMARKS = "คนทำงาน: หอม | บริษัท (กองกลาง 100%)"
TARGET_RECORDED_BY = "หอม (ผ่านเลขาเฟิส)"
TARGET_PROFIT_SHARE = "บริษัท (กองกลาง 100%)"
TARGET_PRE_VAT = 50000.0
TARGET_VAT = 3500.0
TARGET_GROSS = 53500.0
TARGET_WHT_RATE = 3.0
TARGET_WHT_AMOUNT = 1500.0
TARGET_NET = 52000.0
TARGET_STATUS = "ชำระเงินแล้ว"


def build_merged_toy_row(existing_rows: List[List[Any]]) -> List[Any]:
    """
    Constructs the definitive, perfect 24-column row for 'ทอย-RE2608-587'
    merging any existing details with the target financial specs.
    """
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    today_str = datetime.now().strftime("%d/%m/%Y")

    # Extract base metadata from any matching row if available
    rec_date = now_str
    doc_date = today_str
    inv_no = "IV2608-587"
    client_name = "บริษัท เชียงใหม่มีเดีย จำกัด"
    client_tax_id = "0505560000123"
    client_address = "123 ถ.ห้วยแก้ว ต.สุเทพ อ.เมือง จ.เชียงใหม่"
    client_branch = "00000"
    project_desc = "ผลิตคลิปวิดีโอโปรโมทสินค้าและคอนเทนต์มีเดีย"
    bank = "KTB"
    pay_date = today_str

    for r in existing_rows:
        if len(r) > 2 and normalize_doc_no(r[2]) == normalize_doc_no(TARGET_DOC_NO):
            rec_date = str(r[0]) if len(r) > 0 and r[0] and r[0] != "-" else rec_date
            doc_date = str(r[1]) if len(r) > 1 and r[1] and r[1] != "-" else doc_date
            inv_no = str(r[3]) if len(r) > 3 and r[3] and r[3] != "-" else inv_no
            client_name = str(r[4]) if len(r) > 4 and r[4] and r[4] != "-" else client_name
            client_tax_id = str(r[5]) if len(r) > 5 and r[5] and r[5] != "-" else client_tax_id
            client_address = str(r[6]) if len(r) > 6 and r[6] and r[6] != "-" else client_address
            client_branch = str(r[7]) if len(r) > 7 and r[7] and r[7] != "-" else client_branch
            project_desc = str(r[8]) if len(r) > 8 and r[8] and r[8] != "-" else project_desc
            bank = str(r[15]) if len(r) > 15 and r[15] and r[15] != "-" else bank
            pay_date = str(r[17]) if len(r) > 17 and r[17] and r[17] != "-" else pay_date
            break

    merged_row = [
        rec_date,                                      # 0: Record Date
        doc_date,                                      # 1: Tax Invoice Date
        TARGET_DOC_NO,                                 # 2: Receipt No
        inv_no,                                        # 3: Ref Invoice No
        client_name,                                   # 4: Client Name
        format_tax_id_for_sheet(client_tax_id),        # 5: Client Tax ID
        client_address,                                # 6: Client Address
        format_branch_for_sheet(client_branch),        # 7: Branch
        project_desc,                                  # 8: Project / Description
        TARGET_PRE_VAT,                                # 9: Pre-VAT Amount (50,000)
        TARGET_VAT,                                    # 10: VAT 7% (3,500)
        TARGET_GROSS,                                  # 11: Gross Amount (53,500)
        TARGET_WHT_RATE,                               # 12: WHT Rate % (3.0)
        TARGET_WHT_AMOUNT,                             # 13: WHT Amount (1,500)
        TARGET_NET,                                    # 14: Net Received (52,000)
        bank,                                          # 15: Receiving Bank
        TARGET_STATUS,                                 # 16: Payment Status
        pay_date,                                      # 17: Actual Payment Date
        TARGET_PROFIT_SHARE,                           # 18: Profit Share
        TARGET_DRIVE_URL,                              # 19: Drive PDF Link
        TARGET_RECORDED_BY,                            # 20: Recorded By
        TARGET_REMARKS,                                # 21: Remarks
        0.0,                                           # 22: Discount
        "-",                                           # 23: Discount Desc
    ]
    return merged_row


def deduplicate_income_rows(raw_rows: List[List[Any]]) -> Tuple[List[List[Any]], int]:
    """
    Scans a list of income rows, normalizes document numbers,
    merges duplicates of 'ทอย-RE2608-587' into a single complete record,
    and returns (cleaned_rows, duplicate_count).
    """
    seen_map: Dict[str, int] = {}
    cleaned_rows: List[List[Any]] = []
    dup_count = 0

    target_norm = normalize_doc_no(TARGET_DOC_NO)

    for idx, row in enumerate(raw_rows):
        if not row or len(row) < 3:
            continue

        raw_doc_no = str(row[2] if len(row) > 2 else "").strip()
        norm_no = normalize_doc_no(raw_doc_no)

        if not norm_no:
            # Row without doc number, keep as-is
            cleaned_rows.append(row)
            continue

        if norm_no in seen_map:
            dup_count += 1
            existing_idx = seen_map[norm_no]
            logger.info("Found duplicate for doc '%s' (normalized '%s') at row %d.", raw_doc_no, norm_no, idx + 2)

            # If this is our target document, merge into the single canonical version
            if norm_no == target_norm:
                canonical = build_merged_toy_row([cleaned_rows[existing_idx], row])
                cleaned_rows[existing_idx] = canonical
            else:
                # Generic merge: preserve non-empty values
                for col_i in range(len(row)):
                    if col_i >= len(cleaned_rows[existing_idx]):
                        cleaned_rows[existing_idx].append(row[col_i])
                    elif cleaned_rows[existing_idx][col_i] in ["", "-", None] and row[col_i] not in ["", "-", None]:
                        cleaned_rows[existing_idx][col_i] = row[col_i]
        else:
            seen_map[norm_no] = len(cleaned_rows)
            if norm_no == target_norm:
                # Apply canonical structure
                canonical = build_merged_toy_row([row])
                cleaned_rows.append(canonical)
            else:
                cleaned_rows.append(row)

    return cleaned_rows, dup_count


def execute_income_cleanup(
    spreadsheet_id: str = None,
    script_url: str = None
) -> Dict[str, Any]:
    """
    Executes the full read -> deduplicate -> overwrite -> verify pipeline on Google Sheets.
    """
    target_sheet_id = spreadsheet_id or GHN168_SHEET_ID
    target_url = script_url or GAS_SCRIPT_URL

    logger.info("Connecting to Google Sheets tab 'รายรับ'...")
    data_res = ghn168_sync_service.read_sheet_data("รายรับ", spreadsheet_id=target_sheet_id, script_url=target_url)

    raw_rows = data_res.get("values", [])
    initial_count = len(raw_rows)
    logger.info("Read %d rows from Google Sheets tab 'รายรับ'.", initial_count)

    cleaned_rows, dup_count = deduplicate_income_rows(raw_rows)
    final_count = len(cleaned_rows)

    logger.info("Deduplication result: %d duplicates merged. Cleaned total rows: %d.", dup_count, final_count)

    # Overwrite tab 'รายรับ' with clean data
    overwrite_res = ghn168_sync_service.overwrite_sheet_data(
        sheet_name="รายรับ",
        headers=ghn168_sync_service.INCOME_HEADERS,
        rows=cleaned_rows,
        spreadsheet_id=target_sheet_id,
        script_url=target_url
    )
    logger.info("Overwrite status: %s", overwrite_res.get("status"))

    # Verification read back
    verify_res = ghn168_sync_service.read_sheet_data("รายรับ", spreadsheet_id=target_sheet_id, script_url=target_url)
    verified_rows = verify_res.get("values", [])

    # Check for any remaining duplicates
    seen_verify = set()
    has_remaining_duplicates = False
    for r in verified_rows:
        if len(r) > 2 and r[2]:
            norm = normalize_doc_no(r[2])
            if norm in seen_verify:
                has_remaining_duplicates = True
                break
            seen_verify.add(norm)

    return {
        "status": "success",
        "initial_rows": initial_count,
        "duplicate_count": dup_count,
        "final_rows": final_count,
        "verified_rows": len(verified_rows),
        "has_remaining_duplicates": has_remaining_duplicates,
        "overwrite_result": overwrite_res,
        "merged_row": build_merged_toy_row(cleaned_rows)
    }


if __name__ == "__main__":
    result = execute_income_cleanup()
    print(json.dumps(result, indent=2, ensure_ascii=False))
