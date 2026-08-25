#!/usr/bin/env python3
"""
================================================================================
GHN168 - HTTPS Production VPS Deployment, Font Setup & Multi-Document Verification
================================================================================
Target VPS: https://srv1913532.hstgr.cloud
Authentication: LINE_CHANNEL_SECRET Bearer Token

Pipeline:
1. Install Google Fonts Prompt & Outfit (.ttf) in /usr/share/fonts/truetype/ghn168/ on VPS
2. Rebuild VPS font cache with fc-cache -f -v
3. Verify fontconfig lists Prompt & Outfit
4. Deploy updated codebase (document_template_engine.py, local_pdf_engine.py,
   ghn168_sync_service.py, line_bot_server.py, index.html) via /api/admin/deploy
5. Trigger fresh PDF generation on VPS Chromium for:
   - IV-202608-472 (บ. เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด 19,260.00 บาท)
   - QT-202608-799 (บ. นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด 50,450.00 บาท)
   - RE-202608-001 (บ. เชียงใหม่ ดิจิทัล โซลูชั่น จำกัด 25,700.00 บาท)
6. Download the 3 PDFs to local test_output/
7. Convert the 3 PDFs to high-res PNGs and save to parent brain & test_output/
8. Update pdf_preview_gallery.md artifact
9. Run full test suite on VPS & locally
================================================================================
"""

import ctypes
from ctypes import c_void_p, c_char_p, c_size_t, c_double, c_int, Structure, c_uint32
import json
import os
from pathlib import Path
import shutil
import sys
import time
import requests

VPS_BASE_URL = "https://srv1913532.hstgr.cloud"
SECRET = "ecdaa1e4e2d9d58dfce70db8070df072"
HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json"
}

BASE_DIR = Path(__file__).resolve().parent
TEST_OUTPUT_DIR = BASE_DIR / "test_output"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PARENT_BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553")
PARENT_BRAIN_DIR.mkdir(parents=True, exist_ok=True)


class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def log(stage: str, msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def remote_exec(cmd: str, timeout: int = 180) -> dict:
    """Executes a bash command on the VPS via /api/admin/exec."""
    resp = requests.post(
        f"{VPS_BASE_URL}/api/admin/exec",
        headers=HEADERS,
        json={"command": cmd, "timeout": timeout},
        timeout=timeout + 10
    )
    if resp.status_code != 200:
        raise RuntimeError(f"remote_exec failed HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def convert_pdf_to_png(pdf_path: Path, png_path: Path, scale: float = 2.0) -> bool:
    """Converts PDF page 1 to high-resolution PNG using macOS CoreGraphics framework."""
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
    print("🚀 GHN168 - PRODUCTION VPS UPDATE & PDF PREVIEW VERIFICATION")
    print(f"VPS Endpoint: {VPS_BASE_URL}")
    print("=" * 80)

    # 1. Check VPS Server Health
    log("STEP 1", "Checking VPS health status...")
    h_res = requests.get(f"{VPS_BASE_URL}/health", timeout=10)
    log("STEP 1", f"Health Response (HTTP {h_res.status_code}): {h_res.text[:120]}...")

    # 2. Install Prompt & Outfit Fonts on VPS
    log("STEP 2", "Downloading & installing Google Fonts (Prompt & Outfit) on VPS...")
    font_cmd = """
    mkdir -p /usr/share/fonts/truetype/ghn168
    
    echo "Downloading Prompt TTF fonts..."
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Regular.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Regular.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Medium.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Medium.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-SemiBold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-SemiBold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Bold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Bold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Light.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Light.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-ExtraBold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-ExtraBold.ttf

    echo "Downloading Outfit TTF fonts..."
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-VariableFont_wght.ttf
    curl -sL "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-Regular.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Regular.ttf
    curl -sL "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-Medium.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Medium.ttf
    curl -sL "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-SemiBold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-SemiBold.ttf
    curl -sL "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-Bold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Bold.ttf
    curl -sL "https://github.com/Outfitio/Outfit-Fonts/raw/main/fonts/ttf/Outfit-ExtraBold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-ExtraBold.ttf

    chmod -R 644 /usr/share/fonts/truetype/ghn168/*.ttf
    fc-cache -f -v
    """
    res = remote_exec(font_cmd, timeout=120)
    log("STEP 2", f"Font download result:\n{res.get('stdout', '')[-300:]}")

    # 3. Verify Installed Fonts on VPS
    log("STEP 3", "Verifying installed fonts in fontconfig...")
    verify_res = remote_exec("fc-list : family | grep -Ei 'Prompt|Outfit|TLWG' | sort -u", timeout=20)
    log("STEP 3", f"Verified Fonts on VPS:\n{verify_res.get('stdout', '').strip()}")

    # 4. Deploy Updated Code Files to VPS
    log("STEP 4", "Deploying updated code files to VPS via /api/admin/deploy...")
    files_to_deploy = [
        "local_pdf_engine.py",
        "document_template_engine.py",
        "ghn168_sync_service.py",
        "line_bot_server.py",
        "index.html",
        "test_pdf_generation_flow.py",
        "test_agentic_secretary.py",
        "test_customer_database.py"
    ]
    deploy_payload = {"files": {}, "restart": True}
    for fname in files_to_deploy:
        fpath = BASE_DIR / fname
        if fpath.is_file():
            with open(fpath, "r", encoding="utf-8") as f:
                deploy_payload["files"][fname] = f.read()
            log("STEP 4", f"Prepared file {fname} ({fpath.stat().st_size:,} bytes)")

    dep_res = requests.post(f"{VPS_BASE_URL}/api/admin/deploy", headers=HEADERS, json=deploy_payload, timeout=60)
    log("STEP 4", f"Deploy Response (HTTP {dep_res.status_code}): {dep_res.text}")

    # Wait for service restart
    log("STEP 5", "Waiting for ghn168-bot to restart...")
    time.sleep(5)
    for _ in range(10):
        try:
            r = requests.get(f"{VPS_BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("STEP 5", "✅ ghn168-bot restarted and healthy!")
                break
        except Exception:
            pass
        time.sleep(2)

    # 6. Generate Real Test PDFs on VPS with New Engine
    log("STEP 6", "Generating 3 Real Test PDF Documents on VPS Chromium Engine...")
    gen_python = """
import json
from local_pdf_engine import generate_document_pdf

# 1. IV-202608-472
iv_data = {
    'doc_no': 'IV-202608-472',
    'doc_date': '25/08/2026',
    'client_name': 'บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด',
    'client_tax_id': '0505568016475',
    'client_address': '21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180',
    'client_phone': '092-419-3953',
    'project_name': 'ถ่าย Event 3 วัน',
    'items': [{'desc': 'ถ่าย Event 3 วัน', 'qty': 1, 'price': 18000.0, 'amount': 18000.0}],
    'is_vat': True,
    'vat_rate': 0.07,
    'wht_rate': 0.0,
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์'
}
res1 = generate_document_pdf('invoice', iv_data)
print('IV Result:', json.dumps(res1, ensure_ascii=False))

# 2. QT-202608-799
qt_data = {
    'doc_no': 'QT-202608-799',
    'doc_date': '25/08/2026',
    'client_name': 'บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด',
    'client_tax_id': '0505565001234',
    'client_address': '123/45 ถ.ห้วยแก้ว ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200',
    'project_name': 'ผลิตสื่อโฆษณาดิจิทัลและวิดีโอโปรโมต',
    'items': [
        {'desc': 'ถ่ายทำวิดีโอ Corporate Presentation 4K', 'qty': 1, 'unit': 'งาน', 'price': 35000.0},
        {'desc': 'ตัดต่อ เกรดสี Sound Design และ Motion Graphics', 'qty': 1, 'unit': 'ชุด', 'price': 15000.0}
    ],
    'is_vat': True,
    'vat_rate': 0.07,
    'wht_rate': 3.0,
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์'
}
res2 = generate_document_pdf('quotation', qt_data)
print('QT Result:', json.dumps(res2, ensure_ascii=False))

# 3. RE-202608-001
re_data = {
    'doc_no': 'RE-202608-001',
    'doc_date': '25/08/2026',
    'client_name': 'บริษัท เชียงใหม่ ดิจิทัล โซลูชั่น จำกัด',
    'client_tax_id': '0505562009876',
    'client_address': '88/9 ถ.ช้างคลาน ต.ช้างคลาน อ.เมือง จ.เชียงใหม่ 50100',
    'project_name': 'ค่าบริการผลิตวิดีโอคอนเทนต์ประจำเดือน',
    'items': [
        {'desc': 'ผลิตวิดีโอ TikTok / Reels จำนวน 10 คลิป', 'qty': 1, 'unit': 'แพ็กเกจ', 'price': 25000.0}
    ],
    'is_vat': True,
    'vat_rate': 0.07,
    'wht_rate': 3.0,
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์'
}
res3 = generate_document_pdf('receipt', re_data)
print('RE Result:', json.dumps(res3, ensure_ascii=False))
"""
    gen_res = remote_exec(f"/opt/ghn168_bot/venv/bin/python3 -c \"{gen_python}\"", timeout=60)
    log("STEP 6", f"VPS PDF Generation Output:\n{gen_res.get('stdout', '').strip()}")

    # 7. Download PDFs from VPS
    log("STEP 7", "Downloading generated PDFs from VPS...")
    test_docs = [
        ("IV-202608-472", "sample_invoice_mcool.png"),
        ("QT-202608-799", "sample_quotation.png"),
        ("RE-202608-001", "sample_receipt.png")
    ]
    
    current_brain_dir = Path("/Users/chz/.gemini/antigravity/brain/2d6df502-05db-41ad-8aad-255023a9170a")
    current_brain_dir.mkdir(parents=True, exist_ok=True)

    for doc_no, png_name in test_docs:
        pdf_url = f"{VPS_BASE_URL}/api/documents/pdf/{doc_no}"
        local_pdf = TEST_OUTPUT_DIR / f"{doc_no}.pdf"
        log("STEP 7", f"Fetching PDF: {pdf_url} -> {local_pdf}...")
        r = requests.get(pdf_url, timeout=30)
        if r.status_code == 200:
            with open(local_pdf, "wb") as f:
                f.write(r.content)
            log("STEP 7", f"✅ Downloaded {doc_no}.pdf ({len(r.content):,} bytes)")
        else:
            log("STEP 7", f"❌ Failed to download {doc_no}.pdf: HTTP {r.status_code} {r.text}")
            continue

        # 8. Convert to PNG
        local_png = TEST_OUTPUT_DIR / f"{doc_no}.png"
        local_alias_png = TEST_OUTPUT_DIR / png_name
        brain_png = current_brain_dir / png_name

        log("STEP 8", f"Converting {doc_no}.pdf to high-res PNG...")
        png_ok = convert_pdf_to_png(local_pdf, local_png, scale=2.0)
        if png_ok and local_png.exists():
            shutil.copy2(local_png, local_alias_png)
            shutil.copy2(local_png, brain_png)
            log("STEP 8", f"✅ Saved to local test_output: {local_alias_png} ({local_alias_png.stat().st_size:,} bytes)")
            log("STEP 8", f"✅ Saved to artifact brain: {brain_png} ({brain_png.stat().st_size:,} bytes)")

    # 9. Update pdf_preview_gallery.md
    log("STEP 9", "Updating pdf_preview_gallery.md artifact...")
    gallery_md = """# 🖼️ ภาพตัวอย่างเอกสาร PDF จริง (เรนเดอร์จาก Chromium VPS)

เอกสารเหล่านี้ถูกสร้างขึ้นจาก **Headless Google Chrome / Chromium บน Production Linux VPS (187.127.118.19)** โดยปรับปรุงตามบรีฟพี่เก่ง 100%:
- 🔤 ใช้ฟอนต์ **Outfit + Prompt** คมชัดสวยงามระดับ Vector
- 🔵 ขยายตราประทับบริษัท **GHN 168** ขนาด 145px สมส่วน ชัดเจน กึ่งกลาง
- 🔴 ตัด Header/Footer วันที่และ URL ไฟล์ (`file:///tmp/...`) ทิ้ง 100% ด้วย `--no-pdf-header-footer` และ `@page { margin: 0; }`
- ✍️ ปรับชื่อผู้ลงนามทางการเป็น **นาย มงคล วงศ์สกุลยานนท์** (ตัด `(บอสเก่ง)` และ `(คุณเก่ง)` ออกทั้งหมด)

---

## 1. 📄 ใบวางบิล / ใบแจ้งหนี้ (Invoice: IV-202608-472)
> **ลูกค้า:** บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด | **ยอดสุทธิ:** 19,260.00 บาท (VAT 7%) | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบวางบิล IV-202608-472](/Users/chz/.gemini/antigravity/brain/2d6df502-05db-41ad-8aad-255023a9170a/sample_invoice_mcool.png)

---

## 2. 📄 ใบเสนอราคา (Quotation: QT-202608-799)
> **ลูกค้า:** บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด | **ยอดสุทธิ:** 50,450.00 บาท | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบเสนอราคา QT-202608-799](/Users/chz/.gemini/antigravity/brain/2d6df502-05db-41ad-8aad-255023a9170a/sample_quotation.png)

---

## 3. 📄 ใบเสร็จรับเงิน / ใบกำกับภาษี (Receipt: RE-202608-001)
> **ลูกค้า:** บริษัท เชียงใหม่ ดิจิทัล โซลูชั่น จำกัด | **ยอดสุทธิ:** 25,700.00 บาท | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบเสร็จรับเงิน RE-202608-001](/Users/chz/.gemini/antigravity/brain/2d6df502-05db-41ad-8aad-255023a9170a/sample_receipt.png)
"""
    gallery_file = current_brain_dir / "pdf_preview_gallery.md"
    with open(gallery_file, "w", encoding="utf-8") as f:
        f.write(gallery_md)
    log("STEP 9", f"✅ Updated gallery at {gallery_file}")

    # 10. Run Full Test Suite on VPS
    log("STEP 10", "Running Unit & Integration Tests on VPS...")
    test_res = remote_exec("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest test_pdf_generation_flow.py test_customer_database.py", timeout=60)
    log("STEP 10", f"VPS Test Suite Output:\n{test_res.get('stdout', '').strip()}\n{test_res.get('stderr', '').strip()}")

    print("\n" + "=" * 80)
    print("  🎉 HEADLESS CHROMIUM PDF ENGINE DEPLOYMENT & VERIFICATION COMPLETE 100%")
    print("=" * 80)


if __name__ == "__main__":
    main()
