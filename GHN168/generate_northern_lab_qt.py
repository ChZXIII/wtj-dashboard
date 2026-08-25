#!/usr/bin/env python3
"""
Generate Quotation 05 for Northern Innovation Lab Co., Ltd.
HTML, PDF (via PDFShift), PNG (via CoreGraphics/ImageIO), and copy to brain artifact dir.
"""

import ctypes
from ctypes import c_void_p, c_char_p, c_size_t, c_double, c_int, Structure, c_uint32
import os
from pathlib import Path
import shutil
import sys
import requests

from document_template_engine import render_document_html

OUTPUT_DIR = Path("/Users/chz/Desktop/ChZ_Agent_Corp/GHN168/test_output")
CALLER_BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/a5af8d1d-7aab-4c8f-b3ba-de8aed382695")
CURRENT_BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/9cbd4ad7-741a-4233-a281-0ef7f2a14b00")
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
    CALLER_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_BRAIN_DIR.mkdir(parents=True, exist_ok=True)


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

    qt_data = {
        "doc_no": "QT-202608-002",
        "doc_date": "20/08/2026",
        "due_date": "19/09/2026",
        "client_name": "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด",
        "client_tax_id": "0505562005678",
        "client_branch": "สำนักงานใหญ่ (00000)",
        "client_address": "88/9 หมู่ 5 ตำบลช้างเผือก อำเภอเมือง จังหวัดเชียงใหม่ 50300",
        "client_phone": "081-987-6543",
        "project_name": "งานถ่ายทำวิดีโอ (ระบบ 2 กล้อง)",
        "payment_terms": "มัดจำ 50% เมื่องวดแรก และ 50% เมื่องานส่งมอบสมบูรณ์",
        "remarks": "ราคานี้รวมทีมงานถ่ายทำพร้อมอุปกรณ์กล้องระดับ 4K Cinema (ระบบ 2 กล้อง) เรียบร้อยแล้ว",
        "items": [
            {
                "desc": "งานถ่ายทำวิดีโอ (ระบบ 2 กล้อง)",
                "qty": 1,
                "price": 55000.0,
                "amount": 55000.0,
                "worker": "เก่ง"
            }
        ],
        "is_vat": True,
        "vat_rate": 0.07,
        "wht_rate": 0.0,
        "discount": 0.0
    }

    html_filename = "05_Quotation_Northern_Lab.html"
    pdf_filename = "05_Quotation_Northern_Lab.pdf"
    png_filename = "sample_05_quotation_northern_lab.png"

    html_path = OUTPUT_DIR / html_filename
    pdf_path = OUTPUT_DIR / pdf_filename
    png_path = OUTPUT_DIR / png_filename

    print(f"\n--- Generating Quotation for Northern Innovation Lab ---")
    html_content = render_document_html("quotation", qt_data)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [HTML CREATED] {html_path} ({len(html_content):,} chars)")

    pdf_ok = convert_to_pdf_pdfshift(html_content, pdf_path)
    if not pdf_ok:
        print("  [ERROR] PDF Generation failed!")
        sys.exit(1)

    png_ok = convert_pdf_to_png(pdf_path, png_path)
    if not png_ok:
        print("  [ERROR] PNG Generation failed!")
        sys.exit(1)

    # Copy PNG to caller brain directory
    dest_caller = CALLER_BRAIN_DIR / png_filename
    shutil.copy2(png_path, dest_caller)
    print(f"  [COPIED TO CALLER BRAIN] {dest_caller}")

    # Also copy PNG to current brain directory
    dest_current = CURRENT_BRAIN_DIR / png_filename
    shutil.copy2(png_path, dest_current)
    print(f"  [COPIED TO CURRENT BRAIN] {dest_current}")

    print("\n[COMPLETE] All files generated and copied successfully!")


if __name__ == "__main__":
    main()
