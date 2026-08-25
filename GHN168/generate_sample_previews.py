#!/usr/bin/env python3
"""
Generate sample HTML, PDF, and PNG documents for layout verification in test_output/
"""

import os
from pathlib import Path
import shutil
import time

from document_template_engine import render_document_html
from generate_test_samples import convert_to_pdf_pdfshift, convert_pdf_to_png

TEST_OUTPUT_DIR = Path("/Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_output")
ARTIFACT_DIR = Path("/Users/chz/.gemini/antigravity/brain/27e8c13f-4b15-41b1-9b76-03cbe5febdb9")

def main():
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Receipt Data (32,100 THB - Lanna Creative Media)
    receipt_data = {
        "doc_no": "RE-202608-001",
        "doc_date": "20/08/2026",
        "due_date": "20/08/2026",
        "client_name": "บริษัท ล้านนา ครีเอทีฟ มีเดีย จำกัด",
        "client_tax_id": "0505561001234",
        "client_branch": "สำนักงานใหญ่ (00000)",
        "client_address": "123/45 ถนนนิมมานเหมินท์ ตำบลสุเทพ อำเภอเมือง จังหวัดเชียงใหม่ 50200",
        "client_phone": "053-123456",
        "project_name": "บริการผลิตและตัดต่อวิดีโอโปรโมทแบรนด์ประจำไตรมาส 3/2026 (รับชำระเสร็จสิ้น)",
        "payment_terms": "ชำระเงินเรียบร้อยผ่านการโอนเงินเข้าบัญชีธนาคารกรุงไทย",
        "remarks": "ได้รับชำระเงินเต็มจำนวนเรียบร้อยแล้ว ขอขอบพระคุณที่ไว้วางใจ GHN168 Media",
        "items": [
            {
                "desc": "ผลิตและถ่ายทำวิดีโอโปรโมทสินค้า ความยาว 60 วินาที (ระดับ 4K Cinema)",
                "amount": 20000.0,
                "worker": "เก่ง"
            },
            {
                "desc": "บันทึกเสียงบรรยายและออกแบบเสียงประกอบ (Voiceover & Sound Mixing)",
                "amount": 10000.0,
                "worker": "เก่ง"
            }
        ],
        "is_vat": True,
        "vat_rate": 0.07,
        "wht_rate": 0.0,
        "discount": 0.0,
        "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
        "signer_title": "กรรมการผู้จัดการ / ผู้มีอำนาจลงนาม"
    }

    # 2. Quotation Data (32,100 THB - Lanna Creative Media)
    quotation_data = {
        "doc_no": "QT-202608-001",
        "doc_date": "20/08/2026",
        "due_date": "19/09/2026",
        "client_name": "บริษัท ล้านนา ครีเอทีฟ มีเดีย จำกัด",
        "client_tax_id": "0505561001234",
        "client_branch": "สำนักงานใหญ่ (00000)",
        "client_address": "123/45 ถนนนิมมานเหมินท์ ตำบลสุเทพ อำเภอเมือง จังหวัดเชียงใหม่ 50200",
        "client_phone": "053-123456",
        "project_name": "โครงการผลิตสื่อวิดีโอโปรโมทแบรนด์ประจำไตรมาส 3/2026",
        "payment_terms": "มัดจำ 50% เมื่องวดแรก และ 50% เมื่องานส่งมอบสมบูรณ์",
        "remarks": "ราคานี้รวมทีมงานถ่ายทำพร้อมอุปกรณ์กล้องระดับ 4K Cinema และตัดต่อ Color Grading เรียบร้อยแล้ว",
        "items": [
            {
                "desc": "ผลิตและถ่ายทำวิดีโอโปรโมทสินค้า ความยาว 60 วินาที (ระดับ 4K Cinema)",
                "amount": 20000.0,
                "worker": "เก่ง"
            },
            {
                "desc": "บันทึกเสียงบรรยายและออกแบบเสียงประกอบ (Voiceover & Sound Mixing)",
                "amount": 10000.0,
                "worker": "เก่ง"
            }
        ],
        "is_vat": True,
        "vat_rate": 0.07,
        "wht_rate": 0.0,
        "discount": 0.0,
        "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
        "signer_title": "กรรมการผู้จัดการ / ผู้มีอำนาจลงนาม"
    }

    # 3. Invoice Data (53,500 THB - Northern Innovation Lab)
    invoice_data = {
        "doc_no": "IV-202608-001",
        "doc_date": "20/08/2026",
        "due_date": "05/09/2026",
        "client_name": "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด",
        "client_tax_id": "0505562005678",
        "client_branch": "สำนักงานใหญ่ (00000)",
        "client_address": "88/9 หมู่ 5 ตำบลช้างเผือก อำเภอเมือง จังหวัดเชียงใหม่ 50300",
        "client_phone": "081-987-6543",
        "project_name": "บริการบริหารจัดการและผลิตสื่อโฆษณาคอนเทนต์ออนไลน์ ประจำเดือนสิงหาคม 2569",
        "payment_terms": "เครดิต 15 วัน (ชำระภายในวันที่ 5 กันยายน 2569)",
        "remarks": "กรุณาโอนเงินเข้าบัญชี บจ. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น ธ.กรุงไทย เลขที่ 520-0-61960-2",
        "items": [
            {
                "desc": "บริการวางแผนกลยุทธ์ ผลิตคอนเทนต์วิดีโอสั้น TikTok & Reels จำนวน 10 คลิป",
                "amount": 35000.0,
                "worker": "เก่ง"
            },
            {
                "desc": "ออกแบบกราฟิกแบนเนอร์โฆษณา Social Media พร้อม Setup แคมเปญ Ads",
                "amount": 15000.0,
                "worker": "เก่ง"
            }
        ],
        "is_vat": True,
        "vat_rate": 0.07,
        "wht_rate": 0.0,
        "discount": 0.0,
        "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
        "signer_title": "กรรมการผู้จัดการ / ผู้มีอำนาจลงนาม"
    }

    samples = [
        ("sample_receipt_preview", "receipt", receipt_data),
        ("sample_quotation_preview", "quotation", quotation_data),
        ("sample_invoice_preview", "invoice", invoice_data),
    ]

    for filename, doc_type, data in samples:
        html_content = render_document_html(doc_type, data)
        html_file = TEST_OUTPUT_DIR / f"{filename}.html"
        pdf_file = TEST_OUTPUT_DIR / f"{filename}.pdf"
        png_file = TEST_OUTPUT_DIR / f"{filename}.png"

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Generated HTML: {html_file.name}")

        # Convert to PDF
        pdf_ok = convert_to_pdf_pdfshift(html_content, pdf_file)
        if pdf_ok and pdf_file.exists():
            png_ok = convert_pdf_to_png(pdf_file, png_file)
            if png_ok and ARTIFACT_DIR.exists():
                artifact_png = ARTIFACT_DIR / f"{filename}.png"
                shutil.copy2(png_file, artifact_png)
                print(f"  📸 Copied PNG to artifact: {artifact_png.name}")
        time.sleep(1)

    print("\n🎉 All samples generated successfully in test_output/!")

if __name__ == "__main__":
    main()
