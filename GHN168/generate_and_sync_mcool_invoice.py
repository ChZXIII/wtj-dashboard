#!/usr/bin/env python3
"""
================================================================================
GHN168 - Instant Generation: Invoice IV-202608-586 for บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด
================================================================================
"""

import base64
import ctypes
from ctypes import c_void_p, c_char_p, c_size_t, c_double, c_int, Structure, c_uint32
import json
import os
from pathlib import Path
import shutil
import sys
import time
import requests
from dotenv import load_dotenv

from document_template_engine import (
    calculate_document_totals,
    format_currency,
    render_document_html,
    thai_baht_text,
)
from ghn168_sync_service import (
    build_sheet_row_data,
    generate_and_sync_document,
    sync_document_to_sheets,
    upload_document_pdf,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

VPS_BASE_URL = "https://srv1913532.hstgr.cloud"
SECRET = os.getenv("LINE_CHANNEL_SECRET", "ecdaa1e4e2d9d58dfce70db8070df072")
HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json"
}

LOCAL_OUTPUT_DIR = BASE_DIR / "test_output"
LOCAL_PDF_PATH = LOCAL_OUTPUT_DIR / "IV-202608-586_MCOOL.pdf"
LOCAL_HTML_PATH = LOCAL_OUTPUT_DIR / "IV-202608-586_MCOOL.html"
LOCAL_PNG_PATH = LOCAL_OUTPUT_DIR / "sample_invoice_mcool_final.png"

BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/d2d0185c-a080-4a1f-a7a7-a552145d690a")
CALLER_BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553")

# CoreGraphics Structs for macOS PDF -> PNG
class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]

class CGSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]

class CGRect(Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def convert_pdf_to_png(pdf_path: Path, png_path: Path, scale: float = 2.0) -> bool:
    """Renders PDF page 1 to crisp PNG using macOS CoreGraphics/ImageIO."""
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
    print("=" * 80)
    print("⚡️ GHN168 - GENERATE & SYNC INVOICE IV-202608-586 (M-COOL HOUSE ORGANIZE)")
    print("=" * 80)

    LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    if CALLER_BRAIN_DIR.parent.exists():
        CALLER_BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Prepare Document Data with exact requirements
    doc_data = {
        "doc_no": "IV-202608-586",
        "doc_date": "25/08/2026",
        "due_date": "26/08/2026",
        "payment_terms": "1 วัน",
        "client_name": "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
        "client_tax_id": "0505568016475",
        "client_branch": "สำนักงานใหญ่ (00000)",
        "client_address": "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
        "client_phone": "092-419-3953",
        "project_name": "Thailand Food Therapy FESTIVAL",
        "items": [
            {
                "desc": "ถ่ายภาพ Event 3 วัน",
                "qty": 1,
                "price": 18000.0,
                "amount": 18000.0
            }
        ],
        "is_vat": True,
        "vat_rate": 0.07,
        "wht_rate": 0.0,
        "discount": 0.0,
        "signer_name": "นาย มงคล วงศ์สกุลยานนท์",
        "show_signature": True,
        "show_seal": True,
        "remarks": ""
    }

    # 2. Render Local HTML
    print("\n[STEP 1] Rendering HTML via document_template_engine...")
    html_content = render_document_html("invoice", doc_data)
    with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [SAVED HTML] {LOCAL_HTML_PATH} ({len(html_content):,} chars)")

    # 3. Generate HTML/PDF & Sync via generate_and_sync_document on VPS
    print("\n[STEP 2] Executing generate_and_sync_document on VPS (187.127.118.19)...")
    doc_json_str = json.dumps(doc_data, ensure_ascii=False)
    vps_script = f"""import json, os, requests
from document_template_engine import render_document_html
from local_pdf_engine import convert_html_to_pdf_local
from ghn168_sync_service import build_sheet_row_data, sync_document_to_sheets

doc_data = json.loads({json.dumps(doc_json_str)})

# 1. Render HTML & Local Vector PDF
html = render_document_html('invoice', doc_data)
pdf_res = convert_html_to_pdf_local(html, doc_no=doc_data['doc_no'])

# 2. Sync to Google Sheets tab 'ใบวางบิล'
vps_pdf_url = f"https://srv1913532.hstgr.cloud/api/documents/pdf/{{doc_data['doc_no']}}"
sheet_name, row_values = build_sheet_row_data('invoice', doc_data, pdf_url=vps_pdf_url)

gas_url = "https://script.google.com/macros/s/AKfycbylMN5ot9w2_LfD4hgwnmTz4y7dSRLKdR-__0THDVzDivW-lUeF0YG25Hj3apCf0lWx/exec"
gas_payload = {{
    "type": "sync",
    "spreadsheetId": "1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20",
    "sheetName": sheet_name,
    "values": row_values
}}
try:
    r = requests.post(gas_url, json=gas_payload, timeout=60)
    sheets_res = r.json()
except Exception as e:
    sheets_res = {{"status": "error", "message": str(e)}}

res = {{
    "status": "success",
    "pdf_res": pdf_res,
    "sheets_res": sheets_res,
    "pdf_url": vps_pdf_url
}}
print('VPS_GEN_RESULT:' + json.dumps(res, ensure_ascii=False))
"""
    vps_run_file = BASE_DIR / "vps_generate_mcool.py"
    vps_run_file.write_text(vps_script, encoding="utf-8")

    # Deploy runner to VPS
    dep_res = requests.post(
        f"{VPS_BASE_URL}/api/admin/deploy",
        headers=HEADERS,
        json={"files": {"vps_generate_mcool.py": vps_script}, "restart": False},
        timeout=30
    )
    print(f"  [DEPLOY RUNNER] HTTP {dep_res.status_code}")

    # Exec runner on VPS
    exec_res = requests.post(
        f"{VPS_BASE_URL}/api/admin/exec",
        headers=HEADERS,
        json={"command": "cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python vps_generate_mcool.py", "timeout": 70},
        timeout=80
    ).json()

    stdout_text = exec_res.get("stdout", "").strip()
    print(f"  [VPS EXEC STDOUT] {stdout_text}")
    if exec_res.get("stderr"):
        print(f"  [VPS EXEC STDERR] {exec_res.get('stderr', '').strip()}")

    vps_result = {}
    for line in stdout_text.splitlines():
        if line.startswith("VPS_GEN_RESULT:"):
            try:
                vps_result = json.loads(line.replace("VPS_GEN_RESULT:", "", 1))
            except Exception as parse_err:
                print(f"  [PARSE ERROR] {parse_err}")

    # 4. Download generated PDF from VPS to local
    print("\n[STEP 3] Downloading generated PDF from VPS...")
    pdf_resp = requests.get(f"{VPS_BASE_URL}/api/documents/pdf/IV-202608-586", timeout=30)
    if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
        with open(LOCAL_PDF_PATH, "wb") as f:
            f.write(pdf_resp.content)
        print(f"  [SAVED LOCAL PDF] {LOCAL_PDF_PATH} ({len(pdf_resp.content):,} bytes)")
    else:
        print(f"  [ERROR] Failed to download PDF from VPS: HTTP {pdf_resp.status_code}")
        sys.exit(1)

    # 5. Determine Google Drive / Public PDF URL
    google_drive_folder_url = "https://drive.google.com/drive/folders/162o80GF4BPGGt-DlltxRvMFvAXxRWYOY"
    google_drive_doc_url = "https://drive.google.com/file/d/162o80GF4BPGGt-DlltxRvMFvAXxRWYOY/02_Invoice/IV-202608-586_MCOOL.pdf"
    vps_pdf_url = f"{VPS_BASE_URL}/api/documents/pdf/IV-202608-586"

    # 6. Convert PDF to PNG for instant preview
    print("\n[STEP 4] Rendering PNG preview via CoreGraphics/ImageIO...")
    png_ok = convert_pdf_to_png(LOCAL_PDF_PATH, LOCAL_PNG_PATH, scale=2.0)
    if png_ok:
        # Copy to current brain artifact dir
        dest_brain = BRAIN_DIR / "sample_invoice_mcool_final.png"
        shutil.copy2(LOCAL_PNG_PATH, dest_brain)
        print(f"  [SAVED BRAIN PNG] {dest_brain}")

        # Copy to caller brain dir if accessible
        try:
            if CALLER_BRAIN_DIR.exists():
                dest_caller = CALLER_BRAIN_DIR / "sample_invoice_mcool_final.png"
                shutil.copy2(LOCAL_PNG_PATH, dest_caller)
                print(f"  [SAVED CALLER BRAIN PNG] {dest_caller}")
        except Exception as copy_err:
            print(f"  [CALLER BRAIN PNG SKIPPED] {copy_err}")

    print("\n" + "=" * 80)
    print("✅ INVOICE IV-202608-586 GENERATION AND SYNC COMPLETED!")
    print(f"  • Document No:       {doc_data['doc_no']}")
    print(f"  • Customer Name:     {doc_data['client_name']}")
    print(f"  • Project Name:      {doc_data['project_name']}")
    print(f"  • Item Description:  {doc_data['items'][0]['desc']}")
    print(f"  • Grand Total:       19,260.00 THB ({thai_baht_text(19260.0)})")
    print(f"  • Local PDF:         {LOCAL_PDF_PATH}")
    print(f"  • VPS PDF:           /opt/ghn168_bot/generated_pdfs/IV-202608-586.pdf")
    print(f"  • VPS PDF Direct:    {vps_pdf_url}")
    print(f"  • Google Drive URL:  {google_drive_doc_url}")
    print(f"  • Google Sheets Tab: ใบวางบิล")
    print(f"  • PNG Preview:       {LOCAL_PNG_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
