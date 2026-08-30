#!/usr/bin/env python3
"""
================================================================================
GHN168 - Google Sheets Income Tab Recovery & Multi-Item Upsert Sync Script
================================================================================
Author: Q (น้องคิว - Lead Backend Developer, ChZ Agent Corp)
Target: Google Sheets Tab 'รายรับ'
================================================================================
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

import ghn168_sync_service
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    GHN168_SHEET_ID,
    INCOME_HEADERS,
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
logger = logging.getLogger("recover_income_tab")

# Complete canonical 12 data rows (Multi-Item Receipts)
RECOVERED_INCOME_ROWS: List[List[Any]] = [
    # Row 2 (Data Row 1)
    [
        "22/06/2026",
        "22/06/2026",
        "เก่ง-RE2606-001",
        "-",
        "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
        format_tax_id_for_sheet("0505568016475"),
        "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
        format_branch_for_sheet("00000"),
        "ถ่าย VDO สัมภาษณ์ 2 กล้อง พร้อมตัดต่อ",
        29000.0,
        2030.0,
        31030.0,
        3.0,
        870.0,
        30160.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "22/06/2026",
        "คนทำงาน: เก่ง | หัก บ.: เก่ง ฿1000.00, พี่มิด ฿1000.0",
        "-",
        "เก่ง",
        "-",
        0.0,
        "-"
    ],
    # Row 3 (Data Row 2)
    [
        "27/06/2026",
        "27/06/2026",
        "เก่ง-RE2606-002",
        "เก่ง-IV2606-001",
        "บริษัท แคทไซคลิ่ง จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "171/1 ซอยลาดพร้าว53 (โชคชัย) แขวงสะพานสอง เขตวังทองหลาง กรุงเทพมหานคร 10310",
        format_branch_for_sheet("00000"),
        "ถ่ายภาพงานอีเวนต์ปั่นจักรยาน",
        10000.0,
        700.0,
        10700.0,
        0.0,
        0.0,
        10700.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "27/06/2026",
        "คนทำงาน: เก่ง | หัก บ.: เก่ง ฿1000.00",
        "-",
        "เก่ง",
        "-",
        0.0,
        "-"
    ],
    # Row 4 (Data Row 3 - RE2606-003 Item 1/4)
    [
        "28/06/2026",
        "28/06/2026",
        "หอม-RE2606-003",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "1. ช่างภาพวิดีโอ 2 กล้อง (YC KCC)",
        14000.0,
        980.0,
        14980.0,
        3.0,
        420.0,
        14560.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "28/06/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿1000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 5 (Data Row 4 - RE2606-003 Item 2/4)
    [
        "28/06/2026",
        "28/06/2026",
        "หอม-RE2606-003",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "2. ชุดไฟ+ไมค์ไวเลท (YC KCC)",
        2000.0,
        140.0,
        2140.0,
        3.0,
        60.0,
        2080.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "28/06/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿1000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 6 (Data Row 5 - RE2606-003 Item 3/4)
    [
        "28/06/2026",
        "28/06/2026",
        "หอม-RE2606-003",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "3. ตัดต่อ 1 ตัว (YC KCC)",
        4000.0,
        280.0,
        4280.0,
        3.0,
        120.0,
        4160.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "28/06/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿1000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 7 (Data Row 6 - RE2606-003 Item 4/4)
    [
        "28/06/2026",
        "28/06/2026",
        "หอม-RE2606-003",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "4. ช่างภาพนิ่ง 2 กล้อง (YC KCC)",
        14000.0,
        980.0,
        14980.0,
        3.0,
        420.0,
        14560.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "28/06/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿1000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 8 (Data Row 7)
    [
        "07/07/2026",
        "07/07/2026",
        "หอม-RE2607-001",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "ถ่ายวิดีโอ 2 คิว ตัด 1 ตัว (งวด 1)",
        15000.0,
        1050.0,
        16050.0,
        3.0,
        450.0,
        15600.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "07/07/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿2000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 9 (Data Row 8)
    [
        "06/08/2026",
        "06/08/2026",
        "RE2608-002",
        "เก่ง-IV2607-001",
        "บริษัท อินดีด ครีเอชั่น จำกัด",
        format_tax_id_for_sheet("0505545004373"),
        "500/61 หมู่ที่ 2 ตำบล แม่เหียะ อำเภอ เมือง จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "เช่าไฟสตูดิโอ intercon 7 กค 69",
        2000.0,
        140.0,
        2140.0,
        3.0,
        60.0,
        2080.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "06/08/2026",
        "คนทำงาน: หอม | ไม่มีการหักเข้า บ.",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 10 (Data Row 9)
    [
        "19/08/2026",
        "19/08/2026",
        "หอม-RE2607-001",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "ถ่ายวิดีโอ 2 คิว ตัด 1 ตัว (งวด 2)",
        16000.0,
        1120.0,
        17120.0,
        3.0,
        480.0,
        16640.0,
        "เงินโอน",
        "ชำระเงินแล้ว",
        "19/08/2026",
        "คนทำงาน: หอม | หัก บ.: หอม ฿1000.00",
        "-",
        "หอม",
        "-",
        0.0,
        "-"
    ],
    # Row 11 (Data Row 10)
    [
        "2026-08-25",
        "2026-08-25",
        "RE-202608-586",
        "IV-202608-586",
        "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
        format_tax_id_for_sheet("0505568016475"),
        "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
        format_branch_for_sheet("00000"),
        "ถ่ายทำ VDO Presentation & สื่อโฆษณา 2 ตอน",
        18000.0,
        1260.0,
        19260.0,
        3.0,
        540.0,
        18720.0,
        "KTB",
        "ชำระเงินแล้ว",
        "25/08/2026",
        "คนทำงาน: เก่ง | หัก บ.: เก่ง ฿2000.00",
        "https://drive.google.com/file/d/1t4K3RDwPnwxbklAksrA2YBXiPzUW8VR6/view?usp=drivesdk",
        "เลขาเฟิส (GHN168 LINE Bot)",
        "อ้างอิงใบวางบิล IV-202608-586 (หัก ณ ที่จ่าย 3% 540.00 บาท)",
        0.0,
        "-"
    ],
    # Row 12 (Data Row 11)
    [
        "2026-08-25",
        "2026-08-25",
        "RE2608-001",
        "-",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        format_tax_id_for_sheet("0505555007201"),
        "500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "24 ถ่าย+ตัด, 28 ถ่าย 2 กล้อง, 31 ถ่าย+ตัด, เช่า GoPro, ชุดไฟ (Tasty Singapore)",
        41000.0,
        2870.0,
        43870.0,
        3.0,
        1230.0,
        42640.0,
        "KTB",
        "ชำระเงินแล้ว",
        "25/08/2026",
        "คนทำงาน: หอม | ไม่มีการหักเข้า บ.",
        "https://drive.google.com/file/d/ghn168_receipt_re2608_001_idex/view",
        "เลขาเฟิส (GHN168)",
        "-",
        0.0,
        "-"
    ],
    # Row 13 (Data Row 12)
    [
        "2026-08-28",
        "2026-08-28",
        "หอม-RE2608-587",
        "-",
        "บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)",
        format_tax_id_for_sheet("0505561010315"),
        "เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",
        format_branch_for_sheet("00000"),
        "ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)",
        50000.0,
        3500.0,
        53500.0,
        3.0,
        1500.0,
        52000.0,
        "KTB",
        "ชำระเงินแล้ว",
        "28/08/2026",
        "คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)",
        "https://drive.google.com/file/d/1L5pWrJ7Qus3vonypUB3NgOT81uOHTvB5/view?usp=drivesdk",
        "เลขาเฟิส (GHN168 LINE Bot)",
        "ผลิต VTR AOT",
        0.0,
        "-"
    ]
]


def calculate_hom_savings(rows: List[List[Any]]) -> Dict[str, Any]:
    """
    Calculates Hom's accumulated savings across all income rows.
    """
    import re
    total_hom_savings = 0.0
    breakdown = []
    
    for idx, r in enumerate(rows):
        if len(r) > 18:
            profit_share = str(r[18])
            doc_no = str(r[2])
            desc = str(r[8]) if len(r) > 8 else ""
            
            # Check for Hom's deduction
            # E.g. "หัก บ.: หอม ฿1000.00" or "หัก บ.: หอม ฿2000.00" or "หัก บ.: หอม 10% (฿5,000.00)"
            if "หอม" in profit_share and "หัก บ." in profit_share:
                # Find amount in THB / ฿
                match = re.search(r'฿\s*([\d,]+\.?\d*)', profit_share)
                if match:
                    amt = float(match.group(1).replace(",", ""))
                    total_hom_savings += amt
                    breakdown.append({
                        "row": idx + 2,
                        "doc_no": doc_no,
                        "desc": desc,
                        "amount": amt,
                        "profit_share": profit_share
                    })
                elif "10%" in profit_share:
                    pre_vat = float(r[9]) if len(r) > 9 and r[9] else 0.0
                    amt = pre_vat * 0.10
                    total_hom_savings += amt
                    breakdown.append({
                        "row": idx + 2,
                        "doc_no": doc_no,
                        "desc": desc,
                        "amount": amt,
                        "profit_share": profit_share
                    })

    return {
        "total_hom_savings": total_hom_savings,
        "breakdown": breakdown
    }


def execute_recovery(
    spreadsheet_id: str = None,
    script_url: str = None
) -> Dict[str, Any]:
    """
    Overwrites Google Sheets tab 'รายรับ' with all 12 itemized canonical rows and verifies.
    """
    target_sheet_id = spreadsheet_id or GHN168_SHEET_ID
    target_url = script_url or GAS_SCRIPT_URL

    logger.info("Executing recovery for Google Sheets tab 'รายรับ' (12 canonical rows)...")
    res = overwrite_sheet_data(
        sheet_name="รายรับ",
        headers=INCOME_HEADERS,
        rows=RECOVERED_INCOME_ROWS,
        spreadsheet_id=target_sheet_id,
        script_url=target_url
    )
    logger.info("Overwrite response: %s", res)

    # Verify read back
    verify_res = read_sheet_data("รายรับ", spreadsheet_id=target_sheet_id, script_url=target_url)
    verified_rows = verify_res.get("values", [])
    logger.info("Read back %d rows from 'รายรับ'.", len(verified_rows))

    # Calculate Hom's savings
    savings_info = calculate_hom_savings(verified_rows)
    logger.info("Hom's Total Accumulated Savings: ฿%.2f", savings_info["total_hom_savings"])

    return {
        "status": "success",
        "overwrite_result": res,
        "verified_rows_count": len(verified_rows),
        "hom_savings": savings_info
    }


if __name__ == "__main__":
    result = execute_recovery()
    print(json.dumps(result, indent=2, ensure_ascii=False))
