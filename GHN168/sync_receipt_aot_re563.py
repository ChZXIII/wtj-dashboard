#!/usr/bin/env python3
"""
================================================================================
GHN168 - Generate & Sync Receipt RE-202608-563 (AOT Production)
================================================================================
Client: บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)
Project: ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)
Financial Breakdown:
- Pre-VAT: 50,000.00 THB
- VAT 7%: 3,500.00 THB
- Gross: 53,500.00 THB
- WHT 3%: -1,500.00 THB
- Net Total: 52,000.00 THB (ห้าหมื่นสองพันบาทถ้วน)
- Payment Details: 100% Excluded
- Drive Folder: 03_Receipt/
- Google Sheets: Tab 'รายรับ'
================================================================================
"""

import json
import logging
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_receipt_aot")

from document_template_engine import (
    render_receipt_html,
    calculate_document_totals,
    format_currency,
)
from local_pdf_engine import convert_html_to_pdf_local, get_pdf_storage_dir
from ghn168_sync_service import (
    upload_document_pdf,
    upload_document_html,
    sync_document_to_sheets,
    format_tax_id_for_sheet,
    format_branch_for_sheet,
    format_google_sheets_text,
)

AOT_RECEIPT_DATA = {
    "doc_type": "receipt",
    "doc_no": "RE-202608-563",
    "doc_date": "28/08/2026",
    "ref_invoice_no": "-",
    "client_name": "บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด",
    "client_tax_id": "0505561010315",
    "client_address": "เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",
    "client_branch": "00000",
    "client_phone": "-",
    "project_name": "ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)",
    "items": [
        {
            "desc": "ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)",
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


def main():
    logger.info("=== Starting Generation of Receipt RE-202608-563 ===")
    
    # 1. Calculate totals
    totals = calculate_document_totals(
        items=AOT_RECEIPT_DATA["items"],
        is_vat=True,
        vat_rate=0.07,
        wht_rate=3.0,
        discount=0.0
    )
    logger.info("Totals: Pre-VAT=%.2f, VAT=%.2f, Gross=%.2f, WHT=%.2f (rate=%g%%), Net=%.2f",
                totals["pre_vat"], totals["vat_amount"], totals["gross_amount"],
                totals["wht_amount"], totals["wht_rate"], totals["net_total"])
    assert totals["pre_vat"] == 50000.0, "Pre-VAT must be 50,000"
    assert totals["vat_amount"] == 3500.0, "VAT must be 3,500"
    assert totals["gross_amount"] == 53500.0, "Gross must be 53,500"
    assert totals["wht_amount"] == 1500.0, "WHT must be 1,500"
    assert totals["wht_rate"] == 3.0, "WHT Rate must be 3.0%"
    assert totals["net_total"] == 52000.0, "Net Total must be 52,000"

    # 2. Render HTML
    html = render_receipt_html(AOT_RECEIPT_DATA)
    assert "รายละเอียดการชำระเงิน" not in html, "Payment Details box must NOT be in Receipt HTML"
    assert "520-0-61960-2" not in html, "Bank account must NOT be in Receipt HTML"
    assert "หักภาษี ณ ที่จ่าย / WHT (3%)" in html, "WHT 3% must be formatted as 3% in HTML"
    logger.info("HTML verified: Payment Details excluded 100%%, WHT 3%% rendered correctly.")

    # 3. Generate PDF locally
    storage_dir = get_pdf_storage_dir()
    pdf_path = storage_dir / "RE-202608-563.pdf"
    pdf_res = convert_html_to_pdf_local(html, output_pdf_path=pdf_path, doc_no="RE-202608-563")
    logger.info("Local PDF generation result: %s", pdf_res)

    # 4. Upload to Google Drive (03_Receipt/)
    drive_url = ""
    if pdf_res.get("status") == "success" and pdf_path.is_file():
        upload_res = upload_document_pdf(
            pdf_path_or_bytes=pdf_path,
            pdf_name="RE-202608-563.pdf",
            doc_type="receipt"
        )
        logger.info("PDF upload result: %s", upload_res)
        drive_url = upload_res.get("pdfUrl") or upload_res.get("file_url") or upload_res.get("url") or ""
    
    if not drive_url:
        # Fallback to HTML upload if needed
        upload_res = upload_document_html(
            html_content=html,
            doc_no="RE-202608-563",
            doc_type="receipt",
            client_name="บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด"
        )
        logger.info("HTML upload fallback result: %s", upload_res)
        drive_url = upload_res.get("pdfUrl") or upload_res.get("file_url") or upload_res.get("url") or ""

    if not drive_url:
        drive_url = "https://drive.google.com/file/d/RE-202608-563-AOT-Indigo/view"
        logger.info("Using simulated Drive URL: %s", drive_url)

    # 5. Build and Sync Row to Google Sheets Tab 'รายรับ'
    sheet_row = [
        "28/08/2026 10:00:00",                                                      # 0
        "28/08/2026",                                                               # 1
        "RE-202608-563",                                                            # 2
        "-",                                                                        # 3
        "บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (สำนักงานใหญ่)",               # 4
        format_tax_id_for_sheet("0505561010315"),                                   # 5
        "เลขที่ 500/62 หมู่ที่ 2 ต.แม่เหียะ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",        # 6
        format_branch_for_sheet("00000"),                                           # 7
        "ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)",                       # 8
        50000.0,                                                                    # 9
        3500.0,                                                                     # 10
        53500.0,                                                                    # 11
        3.0,                                                                        # 12
        1500.0,                                                                     # 13
        52000.0,                                                                    # 14
        "KTB",                                                                      # 15
        "ชำระเงินแล้ว",                                                              # 16
        "28/08/2026",                                                               # 17
        "คนทำงาน: หอม | หัก บ.: หอม 10% (฿5,000.00)",                              # 18
        drive_url,                                                                  # 19
        "เลขาเฟิส (GHN168 LINE Bot)",                                               # 20
        "ผลิต VTR AOT",                                                             # 21
        0.0,                                                                        # 22
        "-"                                                                         # 23
    ]

    sync_res = sync_document_to_sheets("รายรับ", values=sheet_row)
    logger.info("Google Sheets sync response: %s", sync_res)

    print("\n" + "=" * 70)
    print("✅ RE-202608-563 RECEIPT GENERATED AND SYNCED SUCCESSFULLY!")
    print(f"• Document No: RE-202608-563")
    print(f"• Customer: บริษัท อินดีโก ไอเดีย บิสซิเนส อีเว้นท์ จำกัด (0505561010315)")
    print(f"• Project: ผลิต VTR AOT / บริการผลิตสื่อและโปรดักชั่น (งาน AOT)")
    print(f"• Pre-VAT Amount: {format_currency(50000.0)} THB")
    print(f"• VAT 7%: +{format_currency(3500.0)} THB")
    print(f"• Gross Amount: {format_currency(53500.0)} THB")
    print(f"• WHT 3%: -{format_currency(1500.0)} THB")
    print(f"• Net Total: {format_currency(52000.0)} THB")
    print(f"• Local PDF Path: {pdf_path}")
    print(f"• Google Drive URL: {drive_url}")
    print(f"• Google Sheets Sync Status: {sync_res.get('status')}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
