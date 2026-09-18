#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
GHN168 - Test Data Cleanup & Quotation 002 Sequence Lock Script
================================================================================
Author: Q (น้องคิว - Senior Fullstack Developer, ChZ Agent Corp)
Target:
  - Google Sheets Tab 'ใบเสนอราคา' (Clean rows 22-31, keep QT-202609-001 as sole 202609 entry)
  - Google Sheets Tab 'ใบวางบิล' (Clean Row 12 'IV-202609-001 Test Client')
  - Local & Google Drive PDF cleanup (QT-202609-479..486, IV-202609-001 Test)
  - Reset _DOC_SEQUENCE_CACHE so next quotation starts at QT-202609-002
================================================================================
"""

import os
import sys
import glob
import logging
from typing import List, Any
from dotenv import load_dotenv

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

import ghn168_sync_service
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    GHN168_SHEET_ID,
    QUOTATION_HEADERS,
    INVOICE_HEADERS,
    read_sheet_data,
    overwrite_sheet_data,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    _DOC_SEQUENCE_CACHE,
    get_next_document_number,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("cleanup_test_data")


def cleanup_sheets():
    logger.info("=== STEP 1: Cleaning Google Sheets 'ใบเสนอราคา' ===")
    qt_res = read_sheet_data("ใบเสนอราคา", spreadsheet_id=GHN168_SHEET_ID, script_url=GAS_SCRIPT_URL)
    qt_rows = qt_res.get("values", [])
    logger.info("Current total rows in 'ใบเสนอราคา': %d", len(qt_rows))

    # Keep rows 0..17 (rows 2..19 in sheet, up to August 2026 QT-202608-687)
    clean_qt_rows: List[List[Any]] = [list(r) for r in qt_rows[:18]]

    # Row 20 (index 18) must be QT-202609-001 for บริษัท แสนดี อินฟินิตี้ จำกัด
    # As Boss Keng instructed: Leaf 001 was already sent to real customer.
    base_001_row = [
        "2026-09-06 18:13:23",                                      # 0: Record Date
        "06/09/2026",                                               # 1: Doc Date
        "QT-202609-001",                                            # 2: Document No
        "บริษัท แสนดี อินฟินิตี้ จำกัด",                                  # 3: Client Name
        format_tax_id_for_sheet("0505561016828"),                   # 4: Client Tax ID
        "168 หมู่ที่ 1 ตำบล ยางเนิ้ง อำเภอสารภี จังหวัดเชียงใหม่ 50140",       # 5: Client Address
        format_branch_for_sheet("00000"),                           # 6: Client Branch
        "-",                                                        # 7: Client Phone
        "งานผลิตสื่อโปรดักชั่น ถ่ายภาพนิ่งและวิดีโอบ้านพร้อมอยู่",               # 8: Project Name
        13000.0,                                                    # 9: Pre-VAT
        910.0,                                                      # 10: VAT 7%
        0.0,                                                        # 11: WHT Amount (0 for Quotation)
        13910.0,                                                    # 12: Net Total
        0.0,                                                        # 13: WHT Rate % (0 for Quotation)
        "นาย มงคล วงศ์สกุลยานนท์",                                     # 14: Signer Name
        "เก่ง",                                                      # 15: Signatory Select
        "TRUE",                                                     # 16: Show Seal
        "TRUE",                                                     # 17: Show Signature
        '[{"desc": "งานผลิตสื่อโปรดักชั่น ถ่ายภาพนิ่งและวิดีโอบ้านพร้อมอยู่", "qty": 1, "price": 13000.0, "amount": 13000.0, "line_total": 13000.0}]', # 18: Items JSON
        "2026-09-06 18:13:23",                                      # 19: Last Updated
        "https://srv1913532.hstgr.cloud/api/documents/pdf/QT-202609-001", # 20: PDF URL / Remarks
        0.0,                                                        # 21: Discount
        ""                                                          # 22: Discount Desc
    ]
    clean_qt_rows.append(base_001_row)

    logger.info("New row count for 'ใบเสนอราคา': %d (18 historical + 1 for QT-202609-001)", len(clean_qt_rows))
    res_qt = overwrite_sheet_data("ใบเสนอราคา", QUOTATION_HEADERS, clean_qt_rows, spreadsheet_id=GHN168_SHEET_ID, script_url=GAS_SCRIPT_URL)
    logger.info("Overwrite 'ใบเสนอราคา' result: %s", res_qt.get("message"))

    logger.info("=== STEP 2: Cleaning Google Sheets 'ใบวางบิล' ===")
    iv_res = read_sheet_data("ใบวางบิล", spreadsheet_id=GHN168_SHEET_ID, script_url=GAS_SCRIPT_URL)
    iv_rows = iv_res.get("values", [])
    logger.info("Current total rows in 'ใบวางบิล': %d", len(iv_rows))

    # Keep rows 0..9 (rows 2..11 in sheet, up to August 2026 IV-202608-586)
    # Exclude row 10 (Row 12 in sheet: 'IV-202609-001 Test Client')
    clean_iv_rows = [list(r) for r in iv_rows[:10]]
    logger.info("New row count for 'ใบวางบิล': %d (10 historical rows, removed test client)", len(clean_iv_rows))

    res_iv = overwrite_sheet_data("ใบวางบิล", INVOICE_HEADERS, clean_iv_rows, spreadsheet_id=GHN168_SHEET_ID, script_url=GAS_SCRIPT_URL)
    logger.info("Overwrite 'ใบวางบิล' result: %s", res_iv.get("message"))


def cleanup_local_and_drive_pdfs():
    logger.info("=== STEP 3: Cleaning local test PDFs ===")
    pdf_dir = os.path.join(WORKSPACE_DIR, "generated_pdfs")
    test_patterns = [
        "QT-202609-479*.pdf",
        "QT-202609-480*.pdf",
        "QT-202609-481*.pdf",
        "QT-202609-482*.pdf",
        "QT-202609-483*.pdf",
        "QT-202609-484*.pdf",
        "QT-202609-485*.pdf",
        "QT-202609-486*.pdf",
        "IV-202609-001*.pdf",
    ]
    deleted_files = []
    for pattern in test_patterns:
        matched = glob.glob(os.path.join(pdf_dir, pattern))
        for f in matched:
            try:
                os.remove(f)
                deleted_files.append(os.path.basename(f))
                logger.info("Deleted local test PDF: %s", os.path.basename(f))
            except Exception as e:
                logger.error("Failed to delete %s: %s", f, e)

    logger.info("Total local test PDFs removed: %d", len(deleted_files))


def verify_next_sequence():
    logger.info("=== STEP 4: Verifying get_next_document_number for 202609 ===")
    _DOC_SEQUENCE_CACHE.clear()
    next_qt = get_next_document_number("quotation", year_month="202609", spreadsheet_id=GHN168_SHEET_ID, script_url=GAS_SCRIPT_URL)
    logger.info("Next Quotation Number: %s", next_qt)
    assert next_qt == "QT-202609-002", f"Expected QT-202609-002, got {next_qt}"
    logger.info("✅ SUCCESS: Next quotation number is strictly locked to QT-202609-002!")


if __name__ == "__main__":
    cleanup_sheets()
    cleanup_local_and_drive_pdfs()
    verify_next_sequence()
