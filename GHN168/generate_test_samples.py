#!/usr/bin/env python3
"""
Generate 4 sample documents (HTML & PDF & PNG) for GHN168 Document Template Engine.
"""

import ctypes
from ctypes import c_void_p, c_char_p, c_size_t, c_double, c_int, Structure, c_uint32
import os
from pathlib import Path
import shutil
import sys
import time
import requests

from document_template_engine import render_document_html

OUTPUT_DIR = Path("/Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_output")
ARTIFACT_DIR = Path("/Users/chz/.gemini/antigravity/brain/467b733e-60fb-49cc-a21d-e58ae66192ea")
PDFSHIFT_API_KEY = "sk_d8cecf2bf72214f73d19e6de9520cacacb8f60ad"
PDFSHIFT_URL = "https://api.pdfshift.io/v3/convert/pdf"


class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if ARTIFACT_DIR.exists():
        print(f"Artifact directory confirmed: {ARTIFACT_DIR}")
    print(f"Output directory confirmed: {OUTPUT_DIR}")


def convert_to_pdf_pdfshift(html_content: str, output_pdf_path: Path, api_key: str = PDFSHIFT_API_KEY) -> bool:
    print(f"Converting to PDF -> {output_pdf_path.name}...")
    payload = {
        "source": html_content,
        "sandbox": False,
        "format": "A4"
    }
    try:
        response = requests.post(
            PDFSHIFT_URL,
            json=payload,
            auth=("api", api_key),
            timeout=60
        )
        if response.status_code in [200, 201]:
            with open(output_pdf_path, "wb") as f:
                f.write(response.content)
            print(f"  [SUCCESS] Created: {output_pdf_path} ({len(response.content):,} bytes)")
            return True
        else:
            print(f"  [ERROR] PDFShift returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  [EXCEPTION] Failed to call PDFShift: {e}")
        return False


def convert_pdf_to_png(pdf_path: Path, png_path: Path, scale: float = 2.0) -> bool:
    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        img_io = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ImageIO.framework/ImageIO")

        cf.CFURLCreateWithFileSystemPath.restype = c_void_p
        cf.CFURLCreateWithFileSystemPath.argtypes = [c_void_p, c_void_p, c_int, c_int]

        cf.CFStringCreateWithCString.restype = c_void_p
        cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]

        cg.CGPDFDocumentCreateWithURL.restype = c_void_p
        cg.CGPDFDocumentCreateWithURL.argtypes = [c_void_p]

        cg.CGPDFDocumentGetPage.restype = c_void_p
        cg.CGPDFDocumentGetPage.argtypes = [c_void_p, c_size_t]

        cg.CGPDFPageGetBoxRect.restype = CGRect
        cg.CGPDFPageGetBoxRect.argtypes = [c_void_p, c_int]

        cg.CGColorSpaceCreateDeviceRGB.restype = c_void_p

        cg.CGBitmapContextCreate.restype = c_void_p
        cg.CGBitmapContextCreate.argtypes = [c_void_p, c_size_t, c_size_t, c_size_t, c_size_t, c_void_p, c_uint32]

        cg.CGBitmapContextCreateImage.restype = c_void_p
        cg.CGBitmapContextCreateImage.argtypes = [c_void_p]

        cg.CGContextSetRGBFillColor.argtypes = [c_void_p, c_double, c_double, c_double, c_double]
        cg.CGContextFillRect.argtypes = [c_void_p, CGRect]
        cg.CGContextScaleCTM.argtypes = [c_void_p, c_double, c_double]
        cg.CGContextDrawPDFPage.argtypes = [c_void_p, c_void_p]

        img_io.CGImageDestinationCreateWithURL.restype = c_void_p
        img_io.CGImageDestinationCreateWithURL.argtypes = [c_void_p, c_void_p, c_size_t, c_void_p]
        img_io.CGImageDestinationAddImage.restype = None
        img_io.CGImageDestinationAddImage.argtypes = [c_void_p, c_void_p, c_void_p]
        img_io.CGImageDestinationFinalize.restype = c_int
        img_io.CGImageDestinationFinalize.argtypes = [c_void_p]

        cf_path_str = cf.CFStringCreateWithCString(None, str(pdf_path.resolve()).encode("utf-8"), 0x08000100)
        url = cf.CFURLCreateWithFileSystemPath(None, cf_path_str, 0, 0)
        pdf = cg.CGPDFDocumentCreateWithURL(url)
        if not pdf:
            print(f"  [ERROR] Could not load PDF: {pdf_path}")
            return False

        page = cg.CGPDFDocumentGetPage(pdf, 1)
        if not page:
            print(f"  [ERROR] Could not get page 1 of PDF: {pdf_path}")
            return False

        rect = cg.CGPDFPageGetBoxRect(page, 0)
        w = int(rect.size.width * scale)
        h = int(rect.size.height * scale)

        cs = cg.CGColorSpaceCreateDeviceRGB()
        ctx = cg.CGBitmapContextCreate(None, w, h, 8, w * 4, cs, 1)

        cg.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
        cg.CGContextFillRect(ctx, CGRect(CGPoint(0, 0), CGSize(w, h)))
        cg.CGContextScaleCTM(ctx, scale, scale)
        cg.CGContextDrawPDFPage(ctx, page)

        image = cg.CGBitmapContextCreateImage(ctx)

        cf_out_str = cf.CFStringCreateWithCString(None, str(png_path.resolve()).encode("utf-8"), 0x08000100)
        out_url = cf.CFURLCreateWithFileSystemPath(None, cf_out_str, 0, 0)
        png_type = cf.CFStringCreateWithCString(None, b"public.png", 0x08000100)
        dest = img_io.CGImageDestinationCreateWithURL(out_url, png_type, 1, None)
        img_io.CGImageDestinationAddImage(dest, image, None)
        success = bool(img_io.CGImageDestinationFinalize(dest))
        if success:
            print(f"  [PNG CREATED] {png_path.name} ({png_path.stat().st_size:,} bytes)")
        return success
    except Exception as e:
        print(f"  [PNG EXCEPTION] {e}")
        return False


def main():
    ensure_dirs()

    # --------------------------------------------------------------------------
    # 1. Quotation Sample (30,000 THB)
    # --------------------------------------------------------------------------
    qt_data = {
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
        "wht_rate": 0.0,
        "discount": 0.0
    }

    # --------------------------------------------------------------------------
    # 2. Invoice Sample (50,000 THB + 7% VAT 3,500 = 53,500 THB)
    # --------------------------------------------------------------------------
    iv_data = {
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
        "wht_rate": 0.0,
        "discount": 0.0
    }

    # --------------------------------------------------------------------------
    # 3. Receipt Sample (32,100 THB = 30,000 + 7% VAT 2,100)
    # --------------------------------------------------------------------------
    re_data = {
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
        "discount": 0.0
    }

    # --------------------------------------------------------------------------
    # 4. WHT 50 Tawi Sample (Khun Hom 15,000 THB)
    # --------------------------------------------------------------------------
    wht_data = {
        "doc_no": "WHT-202608-001",
        "doc_date": "20/08/2026",
        "payee_name": "นางสาว จุฑามาศ ศรีจันทร์ (คุณหอม)",
        "payee_tax_id": "1-5099-01234-56-7",
        "payee_address": "65/1 ถนนต้นขาม 2 ตำบลท่าศาลา อำเภอเมือง จังหวัดเชียงใหม่ 50000",
        "income_desc": "ค่าจ้างงานบริการประสานงานการผลิตสื่อและตัดต่อคอนเทนต์",
        "gross_amount": 15000.0,
        "wht_rate": 3.0
    }

    docs = [
        ("01_Quotation_Sample", "sample_01_quotation.png", "quotation", qt_data),
        ("02_Invoice_Sample", "sample_02_invoice.png", "invoice", iv_data),
        ("03_Receipt_Sample", "sample_03_receipt.png", "receipt", re_data),
        ("04_WHT_50_Tawi_Sample", "sample_04_wht.png", "wht", wht_data),
    ]

    results = []
    for basename, sample_png_name, doc_type, data in docs:
        html_path = OUTPUT_DIR / f"{basename}.html"
        pdf_path = OUTPUT_DIR / f"{basename}.pdf"
        png_path = OUTPUT_DIR / sample_png_name

        print(f"\n--- Processing {basename} ({doc_type}) ---")
        html_content = render_document_html(doc_type, data)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"  [HTML CREATED] {html_path.name} ({len(html_content):,} chars)")

        pdf_ok = convert_to_pdf_pdfshift(html_content, pdf_path)
        png_ok = False
        if pdf_ok and pdf_path.exists():
            png_ok = convert_pdf_to_png(pdf_path, png_path)
            if png_ok and ARTIFACT_DIR.exists():
                dest_artifact_png = ARTIFACT_DIR / sample_png_name
                shutil.copy2(png_path, dest_artifact_png)
                print(f"  [COPIED TO ARTIFACT] {dest_artifact_png}")

        results.append({
            "name": basename,
            "html": html_path,
            "pdf": pdf_path,
            "png": png_path,
            "pdf_ok": pdf_ok,
            "png_ok": png_ok
        })
        time.sleep(1)

    print("\n================ SUMMARY ================")
    for r in results:
        pdf_status = "PDF OK" if r["pdf_ok"] else "PDF FAILED"
        png_status = "PNG OK" if r["png_ok"] else "PNG FAILED"
        print(f"- {r['name']}: HTML ({r['html'].exists()}), {pdf_status}, {png_status}")


if __name__ == "__main__":
    main()
