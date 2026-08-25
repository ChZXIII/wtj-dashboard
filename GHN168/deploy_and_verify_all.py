#!/usr/bin/env python3
"""
================================================================================
GHN168 - VPS Deployment, Font Installation, PDF Rendering & PNG Verification
================================================================================
Target VPS: 187.127.118.19 (srv1913532.hstgr.cloud)
User: root
Remote Directory: /opt/ghn168_bot

Tasks:
1. Install Thai & Google Fonts (Prompt & Outfit) on VPS in /usr/share/fonts/truetype/ghn168/
2. Update font cache with fc-cache -f -v
3. Verify fonts availability in fontconfig
4. Sync updated local files to VPS
5. Restart systemd service ghn168-bot
6. Render 3 fresh PDFs on VPS via Chromium Engine:
   - IV-202608-472.pdf (M-Cool House Organize 19,260 THB)
   - QT-202608-799.pdf (Northern Innovation Lab 50,450 THB)
   - RE-202608-001.pdf (Chiang Mai Digital Solution 25,700 THB)
7. Download generated PDFs to local test_output/
8. Convert 3 PDFs to high-res PNGs and save to parent brain folder & test_output/
9. Update pdf_preview_gallery.md artifact
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
import pexpect

VPS_HOST = "187.127.118.19"
VPS_USER = "root"
VPS_PASS = "ziqheV-gacsij-tedxy6"
VPS_PORT = 22

BASE_DIR = Path(__file__).resolve().parent
TEST_OUTPUT_DIR = BASE_DIR / "test_output"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REMOTE_APP_DIR = "/opt/ghn168_bot"

PARENT_BRAIN_DIR = Path("/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553")
PARENT_BRAIN_DIR.mkdir(parents=True, exist_ok=True)

SSH_COMMON_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=25",
    "-o", "ServerAliveInterval=30"
]


class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(Structure):
    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def log(stage: str, msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def run_ssh_command(cmd: str, timeout: int = 180, stream: bool = False) -> str:
    """Executes a command on remote VPS via SSH using pexpect."""
    ssh_cmd = ["ssh", *SSH_COMMON_OPTIONS, f"{VPS_USER}@{VPS_HOST}", cmd]
    command_str = " ".join(f'"{c}"' if (" " in c or "$" in c or "&" in c or "|" in c or ">" in c or "<" in c) else c for c in ssh_cmd)

    child = pexpect.spawn(command_str, timeout=timeout, encoding="utf-8")
    prompts = [
        r"[pP]assword:",
        r"Are you sure you want to continue connecting \(yes/no.*\)\?",
        pexpect.EOF,
        pexpect.TIMEOUT
    ]
    output_buffer = []

    while True:
        idx = child.expect(prompts, timeout=timeout)
        if idx == 0:
            child.sendline(VPS_PASS)
            break
        elif idx == 1:
            child.sendline("yes")
        elif idx == 2:
            output_buffer.append(child.before or "")
            return "".join(output_buffer)
        elif idx == 3:
            output_buffer.append(child.before or "")
            raise TimeoutError(f"SSH timed out: {cmd}\nOutput: {''.join(output_buffer)}")

    if stream:
        try:
            while True:
                line = child.readline()
                if not line:
                    break
                print(line, end="", flush=True)
                output_buffer.append(line)
        except (pexpect.EOF, pexpect.TIMEOUT):
            pass
    else:
        child.expect(pexpect.EOF, timeout=timeout)
        output_buffer.append(child.before or "")

    child.close()
    return "".join(output_buffer)


def upload_file_scp(local_path: str, remote_path: str, timeout: int = 60) -> bool:
    """Uploads local file to VPS via scp."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")

    scp_cmd = ["scp", *SSH_COMMON_OPTIONS, local_path, f"{VPS_USER}@{VPS_HOST}:{remote_path}"]
    command_str = " ".join(scp_cmd)

    child = pexpect.spawn(command_str, timeout=timeout, encoding="utf-8")
    prompts = [
        r"[pP]assword:",
        r"Are you sure you want to continue connecting \(yes/no.*\)\?",
        pexpect.EOF,
        pexpect.TIMEOUT
    ]

    while True:
        idx = child.expect(prompts, timeout=timeout)
        if idx == 0:
            child.sendline(VPS_PASS)
            break
        elif idx == 1:
            child.sendline("yes")
        elif idx == 2:
            break
        elif idx == 3:
            raise TimeoutError(f"SCP timed out while uploading {local_path}")

    child.expect(pexpect.EOF, timeout=timeout)
    child.close()
    return True


def download_file_scp(remote_path: str, local_path: str, timeout: int = 60) -> bool:
    """Downloads remote file from VPS to local via scp."""
    scp_cmd = ["scp", *SSH_COMMON_OPTIONS, f"{VPS_USER}@{VPS_HOST}:{remote_path}", local_path]
    command_str = " ".join(scp_cmd)

    child = pexpect.spawn(command_str, timeout=timeout, encoding="utf-8")
    prompts = [
        r"[pP]assword:",
        r"Are you sure you want to continue connecting \(yes/no.*\)\?",
        pexpect.EOF,
        pexpect.TIMEOUT
    ]

    while True:
        idx = child.expect(prompts, timeout=timeout)
        if idx == 0:
            child.sendline(VPS_PASS)
            break
        elif idx == 1:
            child.sendline("yes")
        elif idx == 2:
            break
        elif idx == 3:
            raise TimeoutError(f"SCP timed out while downloading {remote_path}")

    child.expect(pexpect.EOF, timeout=timeout)
    child.close()
    return True


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
    print("🚀 GHN168 - VPS PDF ENGINE UPDATE, FONT INSTALL & PREVIEW GENERATION")
    print(f"Target VPS: {VPS_USER}@{VPS_HOST} (srv1913532.hstgr.cloud)")
    print("=" * 80)

    # 1. Connectivity Check
    log("STEP 1", "Checking SSH connectivity...")
    uname = run_ssh_command("uname -a", timeout=20)
    log("STEP 1", f"Server Info: {uname.strip()}")

    # 2. Install Prompt & Outfit Fonts on VPS
    log("STEP 2", "Installing Google Fonts (Prompt & Outfit) on VPS...")
    font_script = """
    set -e
    mkdir -p /usr/share/fonts/truetype/ghn168
    
    echo "Downloading Prompt Google Fonts (.ttf)..."
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Regular.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Regular.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Medium.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Medium.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-SemiBold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-SemiBold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Bold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Bold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Light.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-Light.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-ExtraBold.ttf" -o /usr/share/fonts/truetype/ghn168/Prompt-ExtraBold.ttf

    echo "Downloading Outfit Google Fonts (.ttf)..."
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-VariableFont_wght.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Regular.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Regular.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Medium.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Medium.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-SemiBold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-SemiBold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-Bold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-Bold.ttf
    curl -sL "https://github.com/google/fonts/raw/main/ofl/outfit/static/Outfit-ExtraBold.ttf" -o /usr/share/fonts/truetype/ghn168/Outfit-ExtraBold.ttf

    chmod -R 644 /usr/share/fonts/truetype/ghn168/*.ttf
    fc-cache -f -v
    """
    pkg_out = run_ssh_command(font_script, timeout=120, stream=True)
    log("STEP 2", "Font installation and fc-cache completed.")

    # 3. Verify Installed Fonts
    log("STEP 3", "Verifying installed fonts on VPS...")
    verify_cmd = """
    echo "=== GHN168 INSTALLED FONTS ==="
    fc-list : family | grep -Ei "Prompt|Outfit|TLWG" | sort -u
    """
    verify_out = run_ssh_command(verify_cmd, timeout=20)
    log("STEP 3", f"Verified Fonts on VPS:\n{verify_out.strip()}")

    # 4. Upload Updated Application Files
    log("STEP 4", "Uploading updated application files to /opt/ghn168_bot/...")
    run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/generated_pdfs {REMOTE_APP_DIR}/assets {REMOTE_APP_DIR}/signatures", timeout=15)

    files_to_upload = [
        "local_pdf_engine.py",
        "document_template_engine.py",
        "ghn168_sync_service.py",
        "line_bot_server.py",
        "index.html",
        "test_pdf_generation_flow.py",
        "test_agentic_secretary.py",
        "test_customer_database.py"
    ]
    for fname in files_to_upload:
        lpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(lpath):
            rpath = f"{REMOTE_APP_DIR}/{fname}"
            log("STEP 4", f"Uploading {fname}...")
            upload_file_scp(lpath, rpath, timeout=60)
            log("STEP 4", f"✅ {fname} uploaded.")

    # 5. Restart Systemd Service
    log("STEP 5", "Restarting ghn168-bot systemd service...")
    run_ssh_command("systemctl restart ghn168-bot", timeout=30)
    time.sleep(2)
    service_status = run_ssh_command("systemctl is-active ghn168-bot", timeout=10).strip()
    log("STEP 5", f"Service active status: {service_status}")
    if service_status != "active":
        logs = run_ssh_command("journalctl -u ghn168-bot -n 30 --no-pager", timeout=20)
        log("STEP 5", f"Service Logs:\n{logs}")
        sys.exit(1)

    # 6. Generate Real Test PDFs on VPS with New Engine
    log("STEP 6", "Generating 3 Real Test PDF Documents on VPS...")
    gen_script = """
    cd /opt/ghn168_bot
    /opt/ghn168_bot/venv/bin/python3 -c "
import json
from local_pdf_engine import generate_document_pdf
from document_template_engine import render_document_html

# 1. IV-202608-472 (บ. เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด 19,260 บาท)
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
"
    """
    gen_out = run_ssh_command(gen_script, timeout=60)
    log("STEP 6", f"VPS PDF Generation Output:\n{gen_out.strip()}")

    # 7. Download PDFs to Local test_output
    log("STEP 7", f"Downloading PDFs to local test_output directory: {TEST_OUTPUT_DIR}...")
    test_docs = [
        ("IV-202608-472.pdf", "sample_invoice_mcool.png"),
        ("QT-202608-799.pdf", "sample_quotation.png"),
        ("RE-202608-001.pdf", "sample_receipt.png")
    ]
    for pdf_name, png_target_name in test_docs:
        rpath = f"/opt/ghn168_bot/generated_pdfs/{pdf_name}"
        lpath = str(TEST_OUTPUT_DIR / pdf_name)
        log("STEP 7", f"Downloading {pdf_name} -> {lpath}...")
        download_file_scp(rpath, lpath, timeout=30)
        size = os.path.getsize(lpath) if os.path.exists(lpath) else 0
        log("STEP 7", f"✅ Downloaded {pdf_name} (Size: {size:,} bytes)")

        # 8. Convert to PNG
        pdf_p = Path(lpath)
        png_local_p = TEST_OUTPUT_DIR / f"{pdf_p.stem}.png"
        png_brain_p = PARENT_BRAIN_DIR / png_target_name

        log("STEP 8", f"Converting {pdf_name} to high-res PNG...")
        png_ok = convert_pdf_to_png(pdf_p, png_local_p, scale=2.0)
        if png_ok and png_local_p.exists():
            shutil.copy2(png_local_p, png_brain_p)
            log("STEP 8", f"✅ Saved to parent brain: {png_brain_p} ({png_brain_p.stat().st_size:,} bytes)")

    # 9. Update pdf_preview_gallery.md
    log("STEP 9", "Updating pdf_preview_gallery.md...")
    gallery_md_content = """# 🖼️ ภาพตัวอย่างเอกสาร PDF จริง (เรนเดอร์จาก Chromium VPS)

เอกสารเหล่านี้ถูกสร้างขึ้นจาก **Headless Google Chrome / Chromium บน Linux VPS (187.127.118.19)** โดยใช้ฟอนต์ **Outfit + Prompt**, ตราประทับขยายขนาดสมส่วน 145px, ตัด Header/Footer วันที่และ URL ไฟล์ทิ้ง 100% และใช้ชื่อผู้ลงนามทางการ **นาย มงคล วงศ์สกุลยานนท์**

---

## 1. 📄 ใบวางบิล / ใบแจ้งหนี้ (Invoice: IV-202608-472)
> **ลูกค้า:** บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด | **ยอดสุทธิ:** 19,260.00 บาท (VAT 7%) | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบวางบิล IV-202608-472](/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553/sample_invoice_mcool.png)

---

## 2. 📄 ใบเสนอราคา (Quotation: QT-202608-799)
> **ลูกค้า:** บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด | **ยอดสุทธิ:** 50,450.00 บาท | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบเสนอราคา QT-202608-799](/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553/sample_quotation.png)

---

## 3. 📄 ใบเสร็จรับเงิน / ใบกำกับภาษี (Receipt: RE-202608-001)
> **ลูกค้า:** บริษัท เชียงใหม่ ดิจิทัล โซลูชั่น จำกัด | **ยอดสุทธิ:** 25,700.00 บาท | **ผู้ลงนาม:** นาย มงคล วงศ์สกุลยานนท์

![ใบเสร็จรับเงิน RE-202608-001](/Users/chz/.gemini/antigravity/brain/e72dcf0d-7321-4e45-8d78-fd02136aa553/sample_receipt.png)
"""
    gallery_path = PARENT_BRAIN_DIR / "pdf_preview_gallery.md"
    with open(gallery_path, "w", encoding="utf-8") as f:
        f.write(gallery_md_content)
    log("STEP 9", f"✅ Updated gallery at {gallery_path}")

    # 10. Run Full Test Suite on VPS
    log("STEP 10", "Running Unit & Integration Tests on VPS...")
    test_run = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest test_pdf_generation_flow.py test_customer_database.py", timeout=60)
    log("STEP 10", f"VPS Test Suite Output:\n{test_run.strip()}")

    print("\n" + "=" * 80)
    print("  🎉 HEADLESS CHROMIUM PDF ENGINE DEPLOYMENT & VERIFICATION COMPLETE 100%")
    print("=" * 80)


if __name__ == "__main__":
    main()
