#!/usr/bin/env python3
"""
================================================================================
GHN168 - Clean 'รายรับ' Tab: Deduplicate & Remove Double-Click Trash
================================================================================
Author: Q (น้องคิว - Lead Backend & System Developer)
Target: Google Sheets Tab 'รายรับ'
Details:
- Retains verified receipt 'เก่ง-RE-202609-010' (Ref: หอม-IV-202609-005, บ. ดับเบิล อิมเมจ 2005 จำกัด)
- Removes trash duplicate receipts 'หอม-RE-202609-011' through 'หอม-RE-202609-018'
================================================================================
"""

import json
import logging
import os
import sys

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

import ghn168_sync_service
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    GHN168_SHEET_ID,
    INCOME_HEADERS,
    read_sheet_data,
    overwrite_sheet_data,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("cleanup_hom_re_duplicates")

def execute_cleanup():
    logger.info("Reading current rows from Google Sheets tab 'รายรับ'...")
    res = read_sheet_data("รายรับ")
    raw_rows = res.get("values", [])
    logger.info("Total rows currently in 'รายรับ': %d", len(raw_rows))

    trash_doc_numbers = {f"หอม-RE-202609-{str(i).zfill(3)}" for i in range(11, 19)}
    logger.info("Trash doc numbers to remove: %s", sorted(list(trash_doc_numbers)))

    clean_rows = []
    removed_rows = []

    for idx, row in enumerate(raw_rows):
        doc_no = str(row[2]).strip() if len(row) > 2 else ""
        if doc_no in trash_doc_numbers:
            removed_rows.append((idx, doc_no, row))
        else:
            clean_rows.append(row)

    logger.info("Identified %d trash rows to remove.", len(removed_rows))
    for idx, doc_no, row in removed_rows:
        logger.info("  - Row %d: %s | Customer: %s", idx, doc_no, row[4] if len(row) > 4 else "")

    logger.info("Clean rows to keep: %d rows.", len(clean_rows))

    # Verify real receipt is kept
    kept_doc_numbers = [str(r[2]).strip() for r in clean_rows if len(r) > 2]
    assert "เก่ง-RE-202609-010" in kept_doc_numbers, "ERROR: Real receipt 'เก่ง-RE-202609-010' is missing from clean_rows!"
    for trash in trash_doc_numbers:
        assert trash not in kept_doc_numbers, f"ERROR: Trash receipt {trash} still present in clean_rows!"

    logger.info("Overwriting Google Sheets tab 'รายรับ' with clean rows...")
    overwrite_res = overwrite_sheet_data(
        sheet_name="รายรับ",
        headers=INCOME_HEADERS,
        rows=clean_rows,
        spreadsheet_id=GHN168_SHEET_ID,
        script_url=GAS_SCRIPT_URL
    )
    logger.info("Overwrite response: %s", overwrite_res)

    # Verification read back
    logger.info("Verifying updated rows from Google Sheets tab 'รายรับ'...")
    verify_res = read_sheet_data("รายรับ")
    verified_rows = verify_res.get("values", [])
    logger.info("Read back %d rows from 'รายรับ'.", len(verified_rows))

    verified_doc_numbers = [str(r[2]).strip() for r in verified_rows if len(r) > 2]
    logger.info("Verified doc numbers: %s", verified_doc_numbers)

    assert len(verified_rows) == len(clean_rows), f"Row count mismatch! Expected {len(clean_rows)}, got {len(verified_rows)}"
    assert "เก่ง-RE-202609-010" in verified_doc_numbers, "Verification failed: 'เก่ง-RE-202609-010' not found!"
    for trash in trash_doc_numbers:
        assert trash not in verified_doc_numbers, f"Verification failed: {trash} still exists in verified rows!"

    logger.info("SUCCESS: Tab 'รายรับ' cleaned and verified successfully!")
    return {
        "status": "success",
        "initial_count": len(raw_rows),
        "removed_count": len(removed_rows),
        "final_count": len(verified_rows),
        "verified_doc_numbers": verified_doc_numbers
    }

if __name__ == "__main__":
    result = execute_cleanup()
    print(json.dumps(result, indent=2, ensure_ascii=False))
