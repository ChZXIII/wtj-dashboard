#!/usr/bin/env python3
"""
================================================================================
GHN168 - Fix Tax ID Leading Zeros & Branch Code Formatting on Google Sheets
================================================================================
Target Sheets:
1. `ใบเสนอราคา` (Quotation Tab)
2. `ใบวางบิล` (Invoice Tab)
3. `รายรับ` (Income Tab)

Operations:
- Reads live rows from Google Sheets via GAS Webhook
- Fixes Tax ID (12 digits -> 13 digits with leading '0', e.g. '0505555007201')
- Enforces single quote prefix `'` to preserve String format in Google Sheets
- Fixes Branch code ('0', '00', empty -> '00000')
- Overwrites tabs safely via GAS Webhook
- Re-reads and validates all rows to guarantee 100% data integrity
================================================================================
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Tuple

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

import ghn168_sync_service
from ghn168_sync_service import (
    GAS_SCRIPT_URL,
    GHN168_SHEET_ID,
    QUOTATION_HEADERS,
    INVOICE_HEADERS,
    INCOME_HEADERS,
    read_sheet_data,
    overwrite_sheet_data,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    format_google_sheets_text,
    normalize_doc_no,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("fix_tax_id_leading_zeros")


def fix_quotation_tab() -> Dict[str, Any]:
    """Fixes Tax ID (Col E / idx 4) and Branch (Col G / idx 6) in tab 'ใบเสนอราคา'."""
    sheet_name = "ใบเสนอราคา"
    logger.info("Reading live data from '%s'...", sheet_name)
    raw_data = read_sheet_data(sheet_name)
    rows = raw_data.get("values", [])
    logger.info("Found %d rows in '%s'", len(rows), sheet_name)

    if not rows:
        return {"status": "warning", "message": f"No data found in '{sheet_name}'", "fixed_count": 0, "total_rows": 0, "fixed_tax_count": 0, "fixed_branch_count": 0}

    cleaned_rows = []
    fixed_tax_count = 0
    fixed_branch_count = 0

    for idx, r in enumerate(rows):
        row = list(r)
        # Pad row to match QUOTATION_HEADERS length if needed
        while len(row) < len(QUOTATION_HEADERS):
            row.append("")

        # Col 4 (E): Tax ID
        orig_tax = str(row[4]).strip() if len(row) > 4 else ""
        new_tax = format_tax_id_for_sheet(orig_tax)
        if new_tax != orig_tax:
            fixed_tax_count += 1
        row[4] = new_tax

        # Col 6 (G): Branch
        orig_branch = str(row[6]).strip() if len(row) > 6 else ""
        new_branch = format_branch_for_sheet(orig_branch)
        if new_branch != orig_branch:
            fixed_branch_count += 1
        row[6] = new_branch

        # Col 7 (H): Phone
        if len(row) > 7 and row[7] and row[7] != "-":
            row[7] = format_google_sheets_text(row[7])

        cleaned_rows.append(row)

    logger.info(
        "Overwriting '%s' with %d cleaned rows (Fixed Tax IDs: %d, Fixed Branches: %d)...",
        sheet_name, len(cleaned_rows), fixed_tax_count, fixed_branch_count
    )
    res = overwrite_sheet_data(sheet_name, QUOTATION_HEADERS, cleaned_rows)
    logger.info("Overwrite result for '%s': %s", sheet_name, res.get("message"))

    return {
        "status": res.get("status", "success"),
        "sheet_name": sheet_name,
        "total_rows": len(cleaned_rows),
        "fixed_tax_count": fixed_tax_count,
        "fixed_branch_count": fixed_branch_count,
        "gas_response": res
    }


def fix_invoice_tab() -> Dict[str, Any]:
    """Fixes Tax ID (Col E / idx 4) and Branch (Col G / idx 6) in tab 'ใบวางบิล'."""
    sheet_name = "ใบวางบิล"
    logger.info("Reading live data from '%s'...", sheet_name)
    raw_data = read_sheet_data(sheet_name)
    rows = raw_data.get("values", [])
    logger.info("Found %d rows in '%s'", len(rows), sheet_name)

    if not rows:
        return {"status": "warning", "message": f"No data found in '{sheet_name}'", "fixed_count": 0, "total_rows": 0, "fixed_tax_count": 0, "fixed_branch_count": 0}

    cleaned_rows = []
    fixed_tax_count = 0
    fixed_branch_count = 0

    for idx, r in enumerate(rows):
        row = list(r)
        # Pad row to match INVOICE_HEADERS length if needed
        while len(row) < len(INVOICE_HEADERS):
            row.append("")

        # Col 4 (E): Tax ID
        orig_tax = str(row[4]).strip() if len(row) > 4 else ""
        new_tax = format_tax_id_for_sheet(orig_tax)
        if new_tax != orig_tax:
            fixed_tax_count += 1
        row[4] = new_tax

        # Col 6 (G): Branch
        orig_branch = str(row[6]).strip() if len(row) > 6 else ""
        new_branch = format_branch_for_sheet(orig_branch)
        if new_branch != orig_branch:
            fixed_branch_count += 1
        row[6] = new_branch

        # Col 7 (H): Phone
        if len(row) > 7 and row[7] and row[7] != "-":
            row[7] = format_google_sheets_text(row[7])

        cleaned_rows.append(row)

    logger.info(
        "Overwriting '%s' with %d cleaned rows (Fixed Tax IDs: %d, Fixed Branches: %d)...",
        sheet_name, len(cleaned_rows), fixed_tax_count, fixed_branch_count
    )
    res = overwrite_sheet_data(sheet_name, INVOICE_HEADERS, cleaned_rows)
    logger.info("Overwrite result for '%s': %s", sheet_name, res.get("message"))

    return {
        "status": res.get("status", "success"),
        "sheet_name": sheet_name,
        "total_rows": len(cleaned_rows),
        "fixed_tax_count": fixed_tax_count,
        "fixed_branch_count": fixed_branch_count,
        "gas_response": res
    }


def fix_income_tab() -> Dict[str, Any]:
    """Fixes Tax ID (Col F / idx 5) and Branch (Col H / idx 7) in tab 'รายรับ'."""
    sheet_name = "รายรับ"
    logger.info("Reading live data from '%s'...", sheet_name)
    raw_data = read_sheet_data(sheet_name)
    rows = raw_data.get("values", [])
    logger.info("Found %d rows in '%s'", len(rows), sheet_name)

    if not rows:
        return {"status": "warning", "message": f"No data found in '{sheet_name}'", "fixed_count": 0, "total_rows": 0, "fixed_tax_count": 0, "fixed_branch_count": 0}

    cleaned_rows = []
    fixed_tax_count = 0
    fixed_branch_count = 0

    for idx, r in enumerate(rows):
        row = list(r)
        # Pad row to match INCOME_HEADERS length if needed
        while len(row) < len(INCOME_HEADERS):
            row.append("")

        # Col 5 (F): Customer Tax ID
        orig_tax = str(row[5]).strip() if len(row) > 5 else ""
        new_tax = format_tax_id_for_sheet(orig_tax)
        if new_tax != orig_tax:
            fixed_tax_count += 1
        row[5] = new_tax

        # Col 7 (H): Customer Branch
        orig_branch = str(row[7]).strip() if len(row) > 7 else ""
        new_branch = format_branch_for_sheet(orig_branch)
        if new_branch != orig_branch:
            fixed_branch_count += 1
        row[7] = new_branch

        cleaned_rows.append(row)

    logger.info(
        "Overwriting '%s' with %d cleaned rows (Fixed Tax IDs: %d, Fixed Branches: %d)...",
        sheet_name, len(cleaned_rows), fixed_tax_count, fixed_branch_count
    )
    res = overwrite_sheet_data(sheet_name, INCOME_HEADERS, cleaned_rows)
    logger.info("Overwrite result for '%s': %s", sheet_name, res.get("message"))

    return {
        "status": res.get("status", "success"),
        "sheet_name": sheet_name,
        "total_rows": len(cleaned_rows),
        "fixed_tax_count": fixed_tax_count,
        "fixed_branch_count": fixed_branch_count,
        "gas_response": res
    }


def verify_all_tabs() -> Dict[str, Any]:
    """Re-reads and validates all 3 tabs to verify 13-digit Tax IDs and 5-digit Branch codes."""
    logger.info("Verifying updated data across all 3 tabs...")
    verification_results = {}

    # 1. ใบเสนอราคา
    qt_data = read_sheet_data("ใบเสนอราคา")
    qt_rows = qt_data.get("values", [])
    qt_invalid = []
    for i, r in enumerate(qt_rows):
        tax = str(r[4]).strip().lstrip("'") if len(r) > 4 else ""
        branch = str(r[6]).strip().lstrip("'") if len(r) > 6 else ""
        tax_digits = "".join(filter(str.isdigit, tax))
        if tax_digits and len(tax_digits) != 13:
            qt_invalid.append(f"Row {i+1} ({r[2]}): Tax ID '{tax}' has {len(tax_digits)} digits")
        if branch != "00000" and len(branch) != 5:
            qt_invalid.append(f"Row {i+1} ({r[2]}): Branch '{branch}' is not 5 digits")
    verification_results["ใบเสนอราคา"] = {
        "total_rows": len(qt_rows),
        "valid": len(qt_invalid) == 0,
        "invalid_details": qt_invalid
    }

    # 2. ใบวางบิล
    iv_data = read_sheet_data("ใบวางบิล")
    iv_rows = iv_data.get("values", [])
    iv_invalid = []
    for i, r in enumerate(iv_rows):
        tax = str(r[4]).strip().lstrip("'") if len(r) > 4 else ""
        branch = str(r[6]).strip().lstrip("'") if len(r) > 6 else ""
        tax_digits = "".join(filter(str.isdigit, tax))
        if tax_digits and len(tax_digits) != 13:
            iv_invalid.append(f"Row {i+1} ({r[2]}): Tax ID '{tax}' has {len(tax_digits)} digits")
        if branch != "00000" and len(branch) != 5:
            iv_invalid.append(f"Row {i+1} ({r[2]}): Branch '{branch}' is not 5 digits")
    verification_results["ใบวางบิล"] = {
        "total_rows": len(iv_rows),
        "valid": len(iv_invalid) == 0,
        "invalid_details": iv_invalid
    }

    # 3. รายรับ
    inc_data = read_sheet_data("รายรับ")
    inc_rows = inc_data.get("values", [])
    inc_invalid = []
    for i, r in enumerate(inc_rows):
        tax = str(r[5]).strip().lstrip("'") if len(r) > 5 else ""
        branch = str(r[7]).strip().lstrip("'") if len(r) > 7 else ""
        tax_digits = "".join(filter(str.isdigit, tax))
        if tax_digits and len(tax_digits) != 13:
            inc_invalid.append(f"Row {i+1} ({r[2]}): Tax ID '{tax}' has {len(tax_digits)} digits")
        if branch != "00000" and len(branch) != 5:
            inc_invalid.append(f"Row {i+1} ({r[2]}): Branch '{branch}' is not 5 digits")
    verification_results["รายรับ"] = {
        "total_rows": len(inc_rows),
        "valid": len(inc_invalid) == 0,
        "invalid_details": inc_invalid
    }

    return verification_results


def main():
    print("=" * 75)
    print("  🔧 GHN168 - FIX TAX ID LEADING ZEROS & BRANCH CODE ON GOOGLE SHEETS")
    print("=" * 75)

    # Step 1: Fix Quotation Tab
    qt_res = fix_quotation_tab()
    print(f"✅ ใบเสนอราคา: {qt_res['total_rows']} rows (Fixed Tax: {qt_res['fixed_tax_count']}, Fixed Branch: {qt_res['fixed_branch_count']})")

    # Step 2: Fix Invoice Tab
    iv_res = fix_invoice_tab()
    print(f"✅ ใบวางบิล: {iv_res['total_rows']} rows (Fixed Tax: {iv_res['fixed_tax_count']}, Fixed Branch: {iv_res['fixed_branch_count']})")

    # Step 3: Fix Income Tab
    inc_res = fix_income_tab()
    print(f"✅ รายรับ: {inc_res['total_rows']} rows (Fixed Tax: {inc_res['fixed_tax_count']}, Fixed Branch: {inc_res['fixed_branch_count']})")

    # Step 4: Verification
    print("-" * 75)
    print("  🔍 RE-READING & VERIFYING ALL 3 TABS ON LIVE GOOGLE SHEETS")
    print("-" * 75)
    verif = verify_all_tabs()
    all_passed = True
    for tab, v in verif.items():
        if v["valid"]:
            print(f"  ✅ {tab}: 100% VALID ({v['total_rows']} rows - all Tax IDs 13 digits, all Branches 5 digits)")
        else:
            all_passed = False
            print(f"  ❌ {tab}: FAILED ({len(v['invalid_details'])} invalid rows):")
            for d in v["invalid_details"]:
                print(f"     - {d}")

    print("=" * 75)
    if all_passed:
        print("  🎉 ALL 3 TABS FIXED AND VERIFIED SUCCESSFULLY!")
    else:
        print("  ⚠️ SOME ROWS REQUIRE ATTENTION")
    print("=" * 75)


if __name__ == "__main__":
    main()
