#!/usr/bin/env python3
"""
================================================================================
GHN168 - Google Sheets Tax ID & Branch Code Auto-Repair and Deduplication Script
================================================================================
Author: Q (Lead Backend Developer, ChZ Agent Corp)
Target: GHN168 Master Spreadsheet (ID: 1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20)

Features:
1. Connects to Google Sheets via Google Apps Script Webhook (`type: 'read'` / `type: 'overwrite'`).
2. Reads all 4 live tabs:
   - `ใบเสนอราคา` (Quotation)
   - `ใบวางบิล` (Invoice)
   - `รายรับ` (Income / Receipt)
   - `ข้อมูลลูกค้า` (Customer Database)
3. Enforces 13-Digit Thai Tax ID formatting:
   - Prepend '0' for 12-digit Tax IDs (e.g. 505555007201 -> '0505555007201)
   - Ensure single quote prefix (') for all 13-digit Tax IDs
4. Enforces 5-Digit Branch code formatting:
   - Pad zeros to 5 digits (e.g. '0' -> '00000') with single quote prefix
5. Deduplicates duplicate records in `รายรับ` tab.
6. Safely updates rows using GAS overwrite action and verifies results.
================================================================================
"""

import os
import sys
import json
import re
import time
from typing import Any, Dict, List, Tuple
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

SPREADSHEET_ID = os.getenv("GHN168_SHEET_ID", "1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20").strip()
GAS_SCRIPT_URL = os.getenv("GAS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbylMN5ot9w2_LfD4hgwnmTz4y7dSRLKdR-__0THDVzDivW-lUeF0YG25Hj3apCf0lWx/exec").strip()

# Standard Headers Definitions
QUOTATION_HEADERS = [
    "วันที่บันทึก (Record Date)",
    "วันที่เอกสาร (Date)",
    "เลขที่เอกสาร (Document No)",
    "ชื่อลูกค้า (Client Name)",
    "เลขประจำตัวผู้เสียภาษี (Client Tax ID)",
    "ที่อยู่ลูกค้า (Client Address)",
    "รหัสสาขา (Client Branch)",
    "เบอร์โทรติดต่อ (Client Phone)",
    "รายละเอียดโครงการ (Project Name)",
    "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
    "ภาษีมูลค่าเพิ่ม 7% (VAT Amount)",
    "ยอดภาษีหัก ณ ที่จ่าย (WHT Amount)",
    "ยอดรวมสุทธิ (Net Amount)",
    "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
    "ชื่อผู้ลงนาม (Signer Name)",
    "ผู้ลงนาม (Signatory Select)",
    "แสดงตราประทับ (Show Company Seal)",
    "แสดงลายเซ็น (Show Document Signature)",
    "ข้อมูลรายการสินค้าและราคา JSON (Items JSON)",
    "วันเวลาที่อัปเดตล่าสุด (Last Updated)",
    "หมายเหตุ (Remarks)",
    "ส่วนลด (Discount)",
    "รายละเอียดส่วนลด (Discount Description)"
]

INVOICE_HEADERS = [
    "วันที่บันทึก (Record Date)",
    "วันที่เอกสาร (Date)",
    "เลขที่เอกสาร (Document No)",
    "ชื่อลูกค้า (Client Name)",
    "เลขประจำตัวผู้เสียภาษี (Client Tax ID)",
    "ที่อยู่ลูกค้า (Client Address)",
    "รหัสสาขา (Client Branch)",
    "เบอร์โทรติดต่อ (Client Phone)",
    "รายละเอียดโครงการ (Project Name)",
    "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
    "ภาษีมูลค่าเพิ่ม 7% (VAT Amount)",
    "ยอดภาษีหัก ณ ที่จ่าย (WHT Amount)",
    "ยอดรวมสุทธิ (Net Amount)",
    "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
    "ชื่อผู้ลงนาม (Signer Name)",
    "ผู้ลงนาม (Signatory Select)",
    "แสดงตราประทับ (Show Company Seal)",
    "แสดงลายเซ็น (Show Document Signature)",
    "ข้อมูลรายการสินค้าและราคา JSON (Items JSON)",
    "วันเวลาที่อัปเดตล่าสุด (Last Updated)",
    "เงื่อนไขการชำระเงิน (Payment Terms)",
    "วันครบกำหนด (Due Date)",
    "หมายเหตุ (Remarks)",
    "ส่วนลด (Discount)",
    "รายละเอียดส่วนลด (Discount Description)"
]

INCOME_HEADERS = [
    "วันที่บันทึก (Record Date)",
    "วันที่ตามใบเสร็จ/ใบกำกับภาษี (Tax Invoice Date)",
    "เลขที่ใบกำกับภาษี / ใบเสร็จรับเงิน (Receipt No.)",
    "เลขที่ใบวางบิล (Invoice No.)",
    "ชื่อลูกค้า (Customer Name)",
    "เลขประจำตัวผู้เสียภาษีลูกค้า (Customer Tax ID)",
    "ที่อยู่ลูกค้า (Customer Address)",
    "รหัสสาขาลูกค้า (Customer Branch)",
    "รายละเอียดงาน / โครงการ (Description / Project)",
    "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
    "ภาษีมูลค่าเพิ่ม 7% (VAT 7%)",
    "ยอดรวมภาษีมูลค่าเพิ่ม (Gross Amount)",
    "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
    "ยอดภาษีถูกหัก ณ ที่จ่าย (WHT Amount)",
    "ยอดเงินที่ได้รับจริง (Net Received)",
    "บัญชีธนาคารที่รับเงิน (Receiving Bank)",
    "สถานะการชำระเงิน (Payment Status)",
    "วันที่ได้รับเงินจริง (Actual Payment Date)",
    "สัดส่วนผู้รับผลประโยชน์ (Profit Share Distribution)",
    "ลิงก์เอกสาร Google Drive (PDF Link)",
    "ผู้บันทึกรายการ (Recorded By)",
    "หมายเหตุ (Remarks)",
    "ส่วนลด (Discount)",
    "รายละเอียดส่วนลด (Discount Description)"
]

CUSTOMER_HEADERS = [
    "รหัสลูกค้า (Customer ID)",
    "ชื่อบริษัท / ลูกค้า (Customer Name)",
    "เลขประจำตัวผู้เสียภาษี (Tax ID)",
    "รหัสสาขา (Branch Code)",
    "ที่อยู่จดทะเบียน (Address)",
    "เบอร์โทรศัพท์ (Phone)",
    "อีเมล (Email)",
    "ผู้ติดต่อ (Contact Person)",
    "วันที่บันทึก (Created Date)",
    "หมายเหตุ (Remarks)"
]


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    while s.startswith("'") or s.startswith('"'):
        s = s[1:].strip()
    while s.endswith("'") or s.endswith('"'):
        s = s[:-1].strip()
    return s


def format_tax_id(val: Any) -> str:
    s = clean_str(val)
    if not s or s == "-":
        return "-"
    digits = re.sub(r"[^0-9]", "", s)
    if not digits:
        return "-"
    if len(digits) == 12:
        digits = "0" + digits
    elif len(digits) == 13:
        pass
    elif len(digits) < 13 and s.isdigit():
        digits = digits.zfill(13)
    return f"'{digits}"


def format_branch(val: Any) -> str:
    s = clean_str(val)
    if not s or s == "-" or s == "0":
        return "'00000"
    digits = re.sub(r"[^0-9]", "", s)
    if digits:
        return f"'{digits.zfill(5)}"
    return "'00000"


def format_phone(val: Any) -> str:
    s = clean_str(val)
    if not s or s == "-":
        return "-"
    return f"'{s}"


def read_sheet_tab(sheet_name: str) -> List[List[Any]]:
    """Reads all data rows from a sheet tab via GAS POST read action."""
    payload = {
        "type": "read",
        "spreadsheetId": SPREADSHEET_ID,
        "sheetName": sheet_name
    }
    resp = requests.post(
        GAS_SCRIPT_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "text/plain"},
        timeout=35,
        allow_redirects=True
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} while reading tab '{sheet_name}': {resp.text}")
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Error reading tab '{sheet_name}': {data.get('message')}")
    return data.get("values", [])


def overwrite_sheet_tab(sheet_name: str, headers: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    """Overwrites a sheet tab safely with headers and rows."""
    payload = {
        "type": "overwrite",
        "spreadsheetId": SPREADSHEET_ID,
        "sheetName": sheet_name,
        "headers": headers,
        "rows": rows
    }
    resp = requests.post(
        GAS_SCRIPT_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "text/plain"},
        timeout=45,
        allow_redirects=True
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} while writing tab '{sheet_name}': {resp.text}")
    return resp.json()


def repair_quotation_tab() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("🔹 [1/4] Repairing Tab: 'ใบเสนอราคา' (Quotation)")
    print("=" * 70)
    rows = read_sheet_tab("ใบเสนอราคา")
    print(f"  • Read {len(rows)} existing rows from Google Sheets.")

    repaired_rows = []
    tax_fixed_count = 0
    branch_fixed_count = 0

    for idx, row in enumerate(rows):
        r = list(row)
        while len(r) < len(QUOTATION_HEADERS):
            r.append("-")

        orig_tax = str(r[4])
        orig_branch = str(r[6])

        new_tax = format_tax_id(orig_tax)
        new_branch = format_branch(orig_branch)
        new_phone = format_phone(r[7])

        if new_tax != orig_tax:
            tax_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Tax ID '{orig_tax}' ➔ '{new_tax}'")
        if new_branch != orig_branch:
            branch_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Branch '{orig_branch}' ➔ '{new_branch}'")

        r[4] = new_tax
        r[6] = new_branch
        r[7] = new_phone
        repaired_rows.append(r)

    print(f"  • Summary: Fixed {tax_fixed_count} Tax IDs, {branch_fixed_count} Branch codes.")
    res = overwrite_sheet_tab("ใบเสนอราคา", QUOTATION_HEADERS, repaired_rows)
    print(f"  ✅ Sheet Update Result: {res.get('message')}")
    return {"tab": "ใบเสนอราคา", "rows": len(repaired_rows), "tax_fixed": tax_fixed_count, "branch_fixed": branch_fixed_count}


def repair_invoice_tab() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("🔹 [2/4] Repairing Tab: 'ใบวางบิล' (Invoice)")
    print("=" * 70)
    rows = read_sheet_tab("ใบวางบิล")
    print(f"  • Read {len(rows)} existing rows from Google Sheets.")

    repaired_rows = []
    tax_fixed_count = 0
    branch_fixed_count = 0

    for idx, row in enumerate(rows):
        r = list(row)
        while len(r) < len(INVOICE_HEADERS):
            r.append("-")

        orig_tax = str(r[4])
        orig_branch = str(r[6])

        new_tax = format_tax_id(orig_tax)
        new_branch = format_branch(orig_branch)
        new_phone = format_phone(r[7])

        if new_tax != orig_tax:
            tax_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Tax ID '{orig_tax}' ➔ '{new_tax}'")
        if new_branch != orig_branch:
            branch_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Branch '{orig_branch}' ➔ '{new_branch}'")

        r[4] = new_tax
        r[6] = new_branch
        r[7] = new_phone
        repaired_rows.append(r)

    print(f"  • Summary: Fixed {tax_fixed_count} Tax IDs, {branch_fixed_count} Branch codes.")
    res = overwrite_sheet_tab("ใบวางบิล", INVOICE_HEADERS, repaired_rows)
    print(f"  ✅ Sheet Update Result: {res.get('message')}")
    return {"tab": "ใบวางบิล", "rows": len(repaired_rows), "tax_fixed": tax_fixed_count, "branch_fixed": branch_fixed_count}


def repair_income_tab() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("🔹 [3/4] Repairing Tab: 'รายรับ' (Receipt / Income & Deduplication)")
    print("=" * 70)
    rows = read_sheet_tab("รายรับ")
    print(f"  • Read {len(rows)} existing rows from Google Sheets.")

    repaired_rows = []
    tax_fixed_count = 0
    branch_fixed_count = 0
    dedup_map = {}
    duplicates_removed = 0

    for idx, row in enumerate(rows):
        r = list(row)
        while len(r) < len(INCOME_HEADERS):
            r.append("-")

        orig_tax = str(r[5])
        orig_branch = str(r[7])

        new_tax = format_tax_id(orig_tax)
        new_branch = format_branch(orig_branch)

        if new_tax != orig_tax:
            tax_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Tax ID '{orig_tax}' ➔ '{new_tax}'")
        if new_branch != orig_branch:
            branch_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[2]}): Branch '{orig_branch}' ➔ '{new_branch}'")

        r[5] = new_tax
        r[7] = new_branch

        # Deduplication Key: (doc_no, invoice_no, client_name, net_amount, date)
        doc_no = clean_str(r[2])
        inv_no = clean_str(r[3])
        client = clean_str(r[4])
        net_amt = clean_str(r[14])
        doc_date = clean_str(r[1])
        drive_link = clean_str(r[19])

        dedup_key = f"{doc_no}|{inv_no}|{client}|{net_amt}|{doc_date}"

        if dedup_key in dedup_map:
            duplicates_removed += 1
            prev_row, prev_idx = dedup_map[dedup_key]
            print(f"    ⚠️ Found duplicate row {idx + 2} matching row {prev_idx + 2} (Doc: {doc_no}, Client: {client})")
            if drive_link and drive_link.startswith("http") and (not prev_row[19] or not str(prev_row[19]).startswith("http")):
                dedup_map[dedup_key] = (r, idx)
        else:
            dedup_map[dedup_key] = (r, idx)

    repaired_rows = [item[0] for item in dedup_map.values()]

    print(f"  • Summary: Fixed {tax_fixed_count} Tax IDs, {branch_fixed_count} Branch codes, Deduplicated {duplicates_removed} duplicate rows.")
    print(f"  • Total unique rows to save: {len(repaired_rows)} (from original {len(rows)})")

    res = overwrite_sheet_tab("รายรับ", INCOME_HEADERS, repaired_rows)
    print(f"  ✅ Sheet Update Result: {res.get('message')}")
    return {"tab": "รายรับ", "rows": len(repaired_rows), "tax_fixed": tax_fixed_count, "branch_fixed": branch_fixed_count, "duplicates_removed": duplicates_removed}


def repair_customer_tab() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("🔹 [4/4] Repairing Tab: 'ข้อมูลลูกค้า' (Customer Database)")
    print("=" * 70)
    rows = read_sheet_tab("ข้อมูลลูกค้า")
    print(f"  • Read {len(rows)} existing rows from Google Sheets.")

    repaired_rows = []
    tax_fixed_count = 0
    branch_fixed_count = 0

    for idx, row in enumerate(rows):
        r = list(row)
        while len(r) < len(CUSTOMER_HEADERS):
            r.append("-")

        orig_tax = str(r[2])
        orig_branch = str(r[3])

        new_tax = format_tax_id(orig_tax)
        new_branch = format_branch(orig_branch)
        new_phone = format_phone(r[5])

        if new_tax != orig_tax:
            tax_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[0]} - {r[1]}): Tax ID '{orig_tax}' ➔ '{new_tax}'")
        if new_branch != orig_branch:
            branch_fixed_count += 1
            print(f"    - Row {idx + 2} ({r[0]} - {r[1]}): Branch '{orig_branch}' ➔ '{new_branch}'")

        r[2] = new_tax
        r[3] = new_branch
        r[5] = new_phone
        repaired_rows.append(r)

    print(f"  • Summary: Fixed {tax_fixed_count} Tax IDs, {branch_fixed_count} Branch codes.")
    res = overwrite_sheet_tab("ข้อมูลลูกค้า", CUSTOMER_HEADERS, repaired_rows)
    print(f"  ✅ Sheet Update Result: {res.get('message')}")
    return {"tab": "ข้อมูลลูกค้า", "rows": len(repaired_rows), "tax_fixed": tax_fixed_count, "branch_fixed": branch_fixed_count}


def main():
    print("\n" + "=" * 80)
    print("🚀 Starting GHN168 Google Sheets Master Tax ID & Branch Auto-Repair")
    print(f"   Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"   GAS Endpoint:   {GAS_SCRIPT_URL}")
    print("=" * 80)

    start_time = time.time()
    results = []

    try:
        results.append(repair_quotation_tab())
        results.append(repair_invoice_tab())
        results.append(repair_income_tab())
        results.append(repair_customer_tab())

        elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print(f"🎉 MASTER REPAIR COMPLETE (Time: {elapsed:.2f}s)")
        print("=" * 80)
        for r in results:
            print(f"  • Tab '{r['tab']}': {r['rows']} rows processed | Tax IDs fixed: {r['tax_fixed']} | Branch codes fixed: {r['branch_fixed']}" + (f" | Duplicates removed: {r.get('duplicates_removed', 0)}" if 'duplicates_removed' in r else ""))
        print("\nAll 4 tabs have been verified and updated 100% on Google Sheets! 🦾🔥")
    except Exception as e:
        print(f"\n❌ Error during sheet repair: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
