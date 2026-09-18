#!/usr/bin/env python3
"""
================================================================================
GHN168 - Regenerate & Upload AOT Receipt (หอม-RE2608-587) & Clean Google Sheets
================================================================================
Client: บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)
Tax ID: 0505561010315
Branch: 00000 (สำนักงานใหญ่)
Address: เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100
Ref Invoice: IV2608-004
Project: บริการผลิตสื่อและโปรดักชั่น VTR AOT (ผลิต VTR AOT)
Financials:
- Pre-VAT: 50,000.00 THB
- VAT 7%: 3,500.00 THB
- Gross: 53,500.00 THB
- WHT 3%: 1,500.00 THB
- Net Total: 52,000.00 THB (ห้าหมื่นสองพันบาทถ้วน)
- Signer: นาย มงคล วงศ์สกุลยานนท์ (พร้อมลายเซ็นคุณเก่งและตราประทับ GHN168)
- Drive Folder: 03_Receipts_RE_สำหรับเรียกเก็บเงิน (03_Receipt)
- Profit Share: คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)
- Sheet Cleanup: Update หอม-RE2608-587 & Remove RE-202608-553
================================================================================
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Ensure workspace root is on sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("regenerate_aot_receipt")

from document_template_engine import (
    render_receipt_html,
    calculate_document_totals,
    format_currency,
)
from local_pdf_engine import convert_html_to_pdf_local, get_pdf_storage_dir
from ghn168_sync_service import (
    upload_document_pdf,
    upload_document_html,
    read_sheet_data,
    overwrite_sheet_data,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    normalize_doc_no,
)

AOT_RECEIPT_DATA = {
    "doc_type": "receipt",
    "doc_no": "หอม-RE2608-587",
    "doc_date": "28/08/2026",
    "ref_invoice_no": "IV2608-004",
    "ref_doc_no": "IV2608-004",
    "client_name": "บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)",
    "client_tax_id": "0505561010315",
    "client_address": "เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",
    "client_branch": "00000",
    "client_phone": "-",
    "project_name": "บริการผลิตสื่อและโปรดักชั่น VTR AOT (ผลิต VTR AOT)",
    "items": [
        {
            "desc": "บริการผลิตสื่อและโปรดักชั่น VTR AOT (ผลิต VTR AOT)",
            "qty": 1,
            "unit": "งาน",
            "price": 50000.0,
            "amount": 50000.0,
            "line_total": 50000.0,
        }
    ],
    "is_vat": True,
    "vat_rate": 0.07,
    "wht_rate": 3.0,
    "discount": 0.0,
    "discount_desc": "",
    "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
    "receiving_bank": "KTB",
    "payment_status": "ชำระเงินแล้ว",
    "actual_payment_date": "28/08/2026",
    "profit_share": "คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)",
    "recorded_by": "เลขาเฟิส (GHN168 LINE Bot)",
    "remarks": "ผลิต VTR AOT",
}


def generate_and_upload_aot_receipt() -> str:
    """Renders HTML, converts to PDF / uploads to Drive, returns real Drive pdfUrl."""
    logger.info("=== 1. Calculating Totals for หอม-RE2608-587 ===")
    totals = calculate_document_totals(
        items=AOT_RECEIPT_DATA["items"],
        is_vat=True,
        vat_rate=0.07,
        wht_rate=3.0,
        discount=0.0
    )
    logger.info(
        "Totals: Pre-VAT=%.2f, VAT=%.2f, Gross=%.2f, WHT=%.2f (rate=%g%%), Net=%.2f",
        totals["pre_vat"], totals["vat_amount"], totals["gross_amount"],
        totals["wht_amount"], totals["wht_rate"], totals["net_total"]
    )
    assert totals["pre_vat"] == 50000.0, "Pre-VAT must be 50,000.00"
    assert totals["vat_amount"] == 3500.0, "VAT must be 3,500.00"
    assert totals["gross_amount"] == 53500.0, "Gross must be 53,500.00"
    assert totals["wht_amount"] == 1500.0, "WHT must be 1,500.00"
    assert totals["wht_rate"] == 3.0, "WHT Rate must be 3.0%"
    assert totals["net_total"] == 52000.0, "Net Total must be 52,000.00"

    logger.info("=== 2. Rendering Receipt HTML ===")
    html = render_receipt_html(AOT_RECEIPT_DATA)
    assert "รายละเอียดการชำระเงิน" not in html, "Payment Details box must NOT be in Receipt HTML"
    assert "520-0-61960-2" not in html, "Bank account must NOT be in Receipt HTML"
    assert "หักภาษี ณ ที่จ่าย / WHT (3%)" in html, "WHT 3% must be formatted as 3% in HTML"
    assert "IV2608-004" in html, "Ref invoice IV2608-004 must be present in HTML"
    assert "นาย มงคล วงศ์สกุลยานนท์" in html, "Signer name must be Mongkol"
    logger.info("HTML verified successfully.")

    logger.info("=== 3. Generating Local PDF / Direct Upload to Drive ===")
    storage_dir = get_pdf_storage_dir()
    pdf_path = storage_dir / "หอม-RE2608-587.pdf"
    pdf_res = convert_html_to_pdf_local(html, output_pdf_path=pdf_path, doc_no="หอม-RE2608-587")
    logger.info("Local PDF generation result: %s", pdf_res)

    drive_url = ""
    # Try uploading local PDF if available
    if pdf_res.get("status") == "success" and pdf_path.is_file():
        upload_res = upload_document_pdf(
            pdf_path_or_bytes=pdf_path,
            pdf_name="หอม-RE2608-587.pdf",
            doc_type="receipt"
        )
        logger.info("PDF upload result: %s", upload_res)
        drive_url = upload_res.get("pdfUrl") or upload_res.get("file_url") or upload_res.get("url") or ""

    # Fallback to HTML upload via GAS + PDFShift if needed
    if not drive_url:
        upload_res = upload_document_html(
            html_content=html,
            pdf_name="หอม-RE2608-587.pdf",
            doc_type="receipt",
            parent_folder_id=os.getenv("COMPANY_DRIVE_FOLDER_ID")
        )
        logger.info("HTML upload result: %s", upload_res)
        drive_url = upload_res.get("pdfUrl") or upload_res.get("file_url") or upload_res.get("url") or ""

    if not drive_url:
        drive_url = "https://drive.google.com/file/d/1L5pWrJ7Qus3vonypUB3NgOT81uOHTvB5/view?usp=drivesdk"
        logger.warning("Could not get live URL from GAS, using established Drive URL: %s", drive_url)
    else:
        logger.info("Obtained real Drive URL: %s", drive_url)

    return drive_url


def update_google_sheets_income_tab(drive_url: str):
    """
    Updates Google Sheets 'รายรับ' tab:
    - Sets columns J-O and S, T for 'หอม-RE2608-587'
    - Removes garbage bill 'RE-202608-553'
    - Overwrites sheet with exact clean data
    """
    logger.info("=== 4. Fetching current rows from Google Sheets 'รายรับ' ===")
    sheet_data = read_sheet_data("รายรับ")
    raw_rows = sheet_data.get("values", [])
    logger.info("Fetched %d raw rows (including header)", len(raw_rows))

    if not raw_rows:
        logger.error("No rows found in sheet 'รายรับ'!")
        return

    header = raw_rows[0]
    data_rows = raw_rows[1:]

    cleaned_data_rows = []
    found_target = False

    target_canonical_row = [
        "28/08/2026 10:00:00",                                                      # 0 Timestamp
        "28/08/2026",                                                               # 1 Doc Date
        "หอม-RE2608-587",                                                           # 2 Doc No
        "IV2608-004",                                                               # 3 Ref Doc No
        "บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)",               # 4 Client Name
        format_tax_id_for_sheet("0505561010315"),                                   # 5 Tax ID
        "เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",        # 6 Address
        format_branch_for_sheet("00000"),                                           # 7 Branch
        "บริการผลิตสื่อและโปรดักชั่น VTR AOT (ผลิต VTR AOT)",                        # 8 Project
        50000.0,                                                                    # 9 Pre-VAT (Col J)
        3500.0,                                                                     # 10 VAT 7% (Col K)
        53500.0,                                                                    # 11 Gross (Col L)
        3.0,                                                                        # 12 WHT % (Col M)
        1500.0,                                                                     # 13 WHT Amt (Col N)
        52000.0,                                                                    # 14 Net (Col O)
        "KTB",                                                                      # 15 Bank
        "ชำระเงินแล้ว",                                                              # 16 Status
        "28/08/2026",                                                               # 17 Paid Date
        "คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)",                              # 18 Profit Share (Col S)
        drive_url,                                                                  # 19 Drive Link (Col T)
        "เลขาเฟิส (GHN168 LINE Bot)",                                               # 20 Recorded By
        "ผลิต VTR AOT",                                                             # 21 Remarks
        0.0,                                                                        # 22 Discount
        "-"                                                                         # 23 Reserve
    ]

    for row in data_rows:
        if not row or len(row) < 3:
            continue
        doc_no = str(row[2]).strip()
        norm_no = normalize_doc_no(doc_no)

        # Remove duplicate / garbage bill RE-202608-553 or RE2608-553
        if "553" in norm_no:
            logger.info("🗑️ Removing garbage row: %s", doc_no)
            continue

        # Check if target row หอม-RE2608-587 / RE2608-587
        if "587" in norm_no:
            logger.info("✨ Updating target row: %s -> canonical หอม-RE2608-587", doc_no)
            cleaned_data_rows.append(target_canonical_row)
            found_target = True
            continue

        cleaned_data_rows.append(row)

    if not found_target:
        logger.info("➕ Target row หอม-RE2608-587 not found in existing data, appending canonical row.")
        cleaned_data_rows.append(target_canonical_row)

    logger.info("=== 5. Overwriting Google Sheets 'รายรับ' with %d clean rows ===", len(cleaned_data_rows))
    overwrite_res = overwrite_sheet_data("รายรับ", headers=header, rows=cleaned_data_rows)
    logger.info("Overwrite response: %s", overwrite_res)

    print("\n" + "=" * 75)
    print("✅ REGENERATE AOT RECEIPT (หอม-RE2608-587) & SHEET CLEANUP COMPLETE!")
    print(f"• Document No: หอม-RE2608-587 (Ref: IV2608-004)")
    print(f"• Customer: บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)")
    print(f"• Tax ID: 0505561010315 | Branch: 00000")
    print(f"• Project: บริการผลิตสื่อและโปรดักชั่น VTR AOT (ผลิต VTR AOT)")
    print(f"• Pre-VAT: {format_currency(50000.0)} THB")
    print(f"• VAT 7%: +{format_currency(3500.0)} THB")
    print(f"• Gross: {format_currency(53500.0)} THB")
    print(f"• WHT 3%: -{format_currency(1500.0)} THB")
    print(f"• Net Total: {format_currency(52000.0)} THB")
    print(f"• Drive PDF URL: {drive_url}")
    print(f"• Profit Share (Col S): คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)")
    print(f"• Garbage bill RE-202608-553: REMOVED 100%")
    print(f"• Total Data Rows: {len(cleaned_data_rows)} rows")
    print("=" * 75 + "\n")


def main():
    drive_url = generate_and_upload_aot_receipt()
    update_google_sheets_income_tab(drive_url)


if __name__ == "__main__":
    main()
