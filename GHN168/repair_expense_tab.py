#!/usr/bin/env python3
"""
================================================================================
GHN168 - Google Sheets Expense Tab Recovery & Split Canonical Rows Sync
================================================================================
Target: Google Sheets Tab 'รายจ่าย'
Replaces Row 13 (PV-202609-470) with 2 canonical rows:
  - Row 13: PV-202609-470 (ห้างหุ้นส่วนจำกัด กรีนแอคเคาน์, 2,000 + VAT 140 = 2,140 THB)
  - Row 14: PV-202609-471 (กรมสรรพากร ผ่าน หจก. กรีนแอคเคาน์, ภ.พ.30 advance 8,750 THB)
Total rows become 14 data rows.
================================================================================
"""

import os
import sys
import json
import logging
from typing import List, Any

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

import ghn168_sync_service
from ghn168_sync_service import (
    EXPENSE_HEADERS,
    read_sheet_data,
    overwrite_sheet_data,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("repair_expense_tab")

_CANONICAL_JSON_PATH = os.path.join(WORKSPACE_DIR, "data", "canonical_expense_rows.json")
if os.path.exists(_CANONICAL_JSON_PATH):
    try:
        with open(_CANONICAL_JSON_PATH, "r", encoding="utf-8") as _f:
            CANONICAL_EXPENSE_ROWS: List[List[Any]] = json.load(_f)
    except Exception as _e:
        logger.warning("Could not load %s: %s", _CANONICAL_JSON_PATH, _e)
        CANONICAL_EXPENSE_ROWS = []
else:
    CANONICAL_EXPENSE_ROWS = []


def run_repair():
    logger.info("Reading current data from Google Sheets tab 'รายจ่าย'...")
    res = read_sheet_data("รายจ่าย")
    if res.get("status") != "success":
        logger.error("Failed to read sheet: %s", res.get("message"))
        sys.exit(1)

    existing_rows = res.get("values", [])
    logger.info("Existing rows in 'รายจ่าย': %d", len(existing_rows))

    # Keep rows 0 to 11 (first 12 rows)
    canonical_rows: List[List[Any]] = [list(r) for r in existing_rows[:12]]

    # Row 13: Green Account Monthly Bookkeeping
    row_13 = [
        "16/09/2569",                                                       # 0: วันที่บันทึก
        "16/09/2569",                                                       # 1: วันที่ตามใบเสร็จ/ใบกำกับภาษี
        "PV-202609-470",                                                    # 2: เลขที่เอกสาร
        "ห้างหุ้นส่วนจำกัด กรีนแอคเคาน์",                                    # 3: ชื่อผู้ให้บริการ / คู่ค้า
        format_tax_id_for_sheet("0503556001336"),                           # 4: เลขประจำตัวผู้เสียภาษี
        "111/119 ม.2 ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",                  # 5: ที่อยู่
        format_branch_for_sheet("00000"),                                   # 6: สาขา
        "ค่าบริการทำบัญชี",                                                  # 7: หมวดหมู่ค่าใช้จ่าย
        "ค่าบริการทำบัญชี ประจำเดือนสิงหาคม 2569 (บิล IV0002899)",            # 8: รายละเอียด
        2000.0,                                                             # 9: ยอดก่อน VAT
        140.0,                                                              # 10: VAT 7%
        2140.0,                                                             # 11: ยอดรวมภาษี
        0.0,                                                                # 12: อัตราหัก ณ ที่จ่าย %
        0.0,                                                                # 13: ยอดหัก ณ ที่จ่าย
        "-",                                                                # 14: ประเภทยื่นภาษี/50ทวิ
        2140.0,                                                             # 15: ยอดจ่ายสุทธิ
        "KTB",                                                              # 16: ช่องทางชำระเงิน
        "จ่ายเงินแล้ว",                                                       # 17: สถานะการจ่าย
        "16/09/2569",                                                       # 18: วันที่จ่ายเงิน
        "PV-202609-470",                                                    # 19: เลขที่ 50 ทวิ / อ้างอิง
        "-",                                                                # 20: ลิงก์ไฟล์
        "ยื่นภาษีซื้อแล้ว",                                                   # 21: สถานะภาษี
        "-",                                                                # 22: โครงการ/งาน
        "ค่าบริการทำบัญชีรายเดือน",                                            # 23: หมายเหตุ
        "บอสมด"                                                             # 24: ผู้ขอเบิก / พนักงาน
    ]

    # Row 14: Revenue Department PP30 Advance Payment
    row_14 = [
        "16/09/2569",                                                       # 0: วันที่บันทึก
        "16/09/2569",                                                       # 1: วันที่ตามใบเสร็จ/ใบกำกับภาษี
        "PV-202609-471",                                                    # 2: เลขที่เอกสาร
        "กรมสรรพากร (ผ่าน หจก. กรีนแอคเคาน์)",                               # 3: ชื่อผู้ให้บริการ / คู่ค้า
        format_tax_id_for_sheet("0994000164669"),                           # 4: เลขประจำตัวผู้เสียภาษี
        "111/119 ม.2 ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",                  # 5: ที่อยู่
        format_branch_for_sheet("00000"),                                   # 6: สาขา
        "ภาษีมูลค่าเพิ่มนำส่งสรรพากร (ภ.พ.30)",                                # 7: หมวดหมู่ค่าใช้จ่าย
        "เงินทดรองจ่ายภาษีมูลค่าเพิ่ม ภ.พ.30 เดือนสิงหาคม 2569 (บิล IV0002899)", # 8: รายละเอียด
        8750.0,                                                             # 9: ยอดก่อน VAT
        0.0,                                                                # 10: VAT 7%
        8750.0,                                                             # 11: ยอดรวมภาษี
        0.0,                                                                # 12: อัตราหัก ณ ที่จ่าย %
        0.0,                                                                # 13: ยอดหัก ณ ที่จ่าย
        "-",                                                                # 14: ประเภทยื่นภาษี/50ทวิ
        8750.0,                                                             # 15: ยอดจ่ายสุทธิ
        "KTB",                                                              # 16: ช่องทางชำระเงิน
        "จ่ายเงินแล้ว",                                                       # 17: สถานะการจ่าย
        "16/09/2569",                                                       # 18: วันที่จ่ายเงิน
        "PV-202609-471",                                                    # 19: เลขที่ 50 ทวิ / อ้างอิง
        "-",                                                                # 20: ลิงก์ไฟล์
        "นำส่งภาษีแล้ว",                                                     # 21: สถานะภาษี
        "-",                                                                # 22: โครงการ/งาน
        "เงินทดรองจ่ายภาษี ภ.พ.30 ไม่คิด VAT ซ้ำซ้อน",                        # 23: หมายเหตุ
        "บอสมด"                                                             # 24: ผู้ขอเบิก / พนักงาน
    ]

    canonical_rows.append(row_13)
    canonical_rows.append(row_14)

    logger.info("New total rows to overwrite: %d", len(canonical_rows))
    overwrite_res = overwrite_sheet_data(
        sheet_name="รายจ่าย",
        headers=EXPENSE_HEADERS,
        rows=canonical_rows
    )
    logger.info("Overwrite response: %s", overwrite_res)

    # Verification: Read back and assert 14 rows
    verify_res = read_sheet_data("รายจ่าย")
    verify_rows = verify_res.get("values", [])
    logger.info("Verification: Read back %d rows from 'รายจ่าย'", len(verify_rows))
    assert len(verify_rows) == 14, f"Expected 14 rows, got {len(verify_rows)}"
    assert verify_rows[12][2] == "PV-202609-470", f"Row 13 doc no mismatch: {verify_rows[12][2]}"
    assert verify_rows[13][2] == "PV-202609-471", f"Row 14 doc no mismatch: {verify_rows[13][2]}"
    logger.info("✅ Verification passed: 14 rows confirmed in Google Sheets 'รายจ่าย'!")


if __name__ == "__main__":
    run_repair()
