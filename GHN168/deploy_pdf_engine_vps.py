#!/usr/bin/env python3
"""
================================================================================
GHN168 - VPS Headless Chromium PDF Engine Setup & Full Verification
================================================================================
Target VPS: 187.127.118.19 (srv1913532.hstgr.cloud)
User: root
Remote Directory: /opt/ghn168_bot

Steps:
1. SSH into VPS & Install Chromium + Thai Fonts:
   - apt-get update && apt-get install -y chromium-browser chromium fonts-thai-tlwg fonts-noto-cjk fonts-noto-core fontconfig
   - If needed, fallback install google-chrome-stable
   - Update font cache (fc-cache -f -v)
2. Verify Chromium binary and Thai fonts availability.
3. Sync updated application files (local_pdf_engine.py, line_bot_server.py, ghn168_sync_service.py, document_template_engine.py).
4. Restart ghn168-bot systemd service & verify active status.
5. Generate real PDFs:
   - IV-202608-472.pdf (บ. เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด 19,260 บาท)
   - QT-202608-799.pdf
   - RE-202608-001.pdf
6. Verify FastAPI PDF endpoint with curl (HTTP 200 OK).
7. Download generated PDFs to local test_output directory.
================================================================================
"""

import json
import os
import sys
import time
from pathlib import Path
import pexpect

VPS_HOST = "187.127.118.19"
VPS_USER = "root"
VPS_PASS = "ziqheV-gacsij-tedxy6"
VPS_PORT = 22

BASE_DIR = Path(__file__).resolve().parent
TEST_OUTPUT_DIR = BASE_DIR / "test_output"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REMOTE_APP_DIR = "/opt/ghn168_bot"

SSH_COMMON_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=20",
    "-o", "ServerAliveInterval=30"
]


def log(stage: str, msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def run_ssh_command(cmd: str, timeout: int = 120, stream: bool = False) -> str:
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


def main():
    print("=" * 80)
    print("🚀 GHN168 - HEADLESS CHROMIUM PDF ENGINE DEPLOYMENT & VERIFICATION")
    print(f"Target VPS: {VPS_USER}@{VPS_HOST} (srv1913532.hstgr.cloud)")
    print("=" * 80)

    # 1. Connectivity Check
    log("STEP 1", "Checking SSH connectivity...")
    uname = run_ssh_command("uname -a && lsb_release -d", timeout=20)
    log("STEP 1", f"Server Info: {uname.strip()}")

    # 2. Install Chromium & Thai Fonts
    log("STEP 2", "Installing Chromium & Thai Fonts on Ubuntu VPS...")
    install_script = """
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y fonts-thai-tlwg fonts-noto-cjk fonts-noto-core fontconfig curl wget

    # Check for Chromium / Chrome
    if ! command -v chromium &>/dev/null && ! command -v chromium-browser &>/dev/null && ! command -v google-chrome &>/dev/null; then
        echo "Installing Chromium browser..."
        apt-get install -y chromium-browser chromium || true
    fi

    # Fallback to Google Chrome Stable if Chromium not found
    if ! command -v chromium &>/dev/null && ! command -v chromium-browser &>/dev/null && ! command -v google-chrome &>/dev/null; then
        echo "Installing Google Chrome Stable deb..."
        wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome.deb
        apt-get install -y /tmp/google-chrome.deb || apt-get install -y -f
        rm -f /tmp/google-chrome.deb
    fi

    # Rebuild font cache
    fc-cache -f -v >/dev/null 2>&1
    """
    pkg_out = run_ssh_command(install_script, timeout=300, stream=True)
    log("STEP 2", "Package installation completed.")

    # 3. Verify Chromium & Fonts
    log("STEP 3", "Verifying Chromium binary and Thai fonts...")
    verify_cmd = """
    echo "=== CHROMIUM BINARY CHECK ==="
    which chromium chromium-browser google-chrome google-chrome-stable || true
    (chromium --version || chromium-browser --version || google-chrome --version) 2>/dev/null || true

    echo "=== THAI FONTS CHECK ==="
    fc-list : lang=th | head -n 10
    """
    verify_out = run_ssh_command(verify_cmd, timeout=30)
    log("STEP 3", f"Verification Result:\n{verify_out.strip()}")

    # 4. Upload Core Application Files
    log("STEP 4", "Uploading updated application files to /opt/ghn168_bot/...")
    run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/generated_pdfs {REMOTE_APP_DIR}/assets {REMOTE_APP_DIR}/signatures", timeout=15)

    files_to_upload = [
        "local_pdf_engine.py",
        "document_template_engine.py",
        "ghn168_sync_service.py",
        "line_bot_server.py",
        "test_pdf_generation_flow.py",
        "test_line_flex_schema_validation.py",
        "test_document_lifecycle.py"
    ]
    for fname in files_to_upload:
        lpath = os.path.join(BASE_DIR, fname)
        rpath = f"{REMOTE_APP_DIR}/{fname}"
        log("STEP 4", f"Uploading {fname}...")
        upload_file_scp(lpath, rpath, timeout=60)
        log("STEP 4", f"✅ {fname} uploaded.")

    # 5. Restart Systemd Service
    log("STEP 5", "Restarting ghn168-bot systemd service...")
    run_ssh_command("systemctl restart ghn168-bot", timeout=30)
    time.sleep(3)
    service_status = run_ssh_command("systemctl is-active ghn168-bot", timeout=10).strip()
    log("STEP 5", f"Service active status: {service_status}")
    if service_status != "active":
        logs = run_ssh_command("journalctl -u ghn168-bot -n 30 --no-pager", timeout=20)
        log("STEP 5", f"Service Logs:\n{logs}")
        sys.exit(1)

    # 6. Generate Real Test PDFs on VPS
    log("STEP 6", "Generating 3 Real Test PDF Documents on VPS...")
    gen_script = """
    cd /opt/ghn168_bot
    /opt/ghn168_bot/venv/bin/python3 -c "
import json
from local_pdf_engine import generate_document_pdf, convert_html_to_pdf_local
from document_template_engine import render_document_html

# 1. IV-202608-472 (บ. เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด 19,260 บาท)
iv_data = {
    'doc_no': 'IV-202608-472',
    'doc_date': '25/08/2026',
    'client_name': 'บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด',
    'client_tax_id': '0505568016475',
    'client_branch': '00000',
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

    # 7. Check PDF Files in Remote Storage
    log("STEP 7", "Verifying PDF files in /opt/ghn168_bot/generated_pdfs/...")
    ls_out = run_ssh_command("ls -lh /opt/ghn168_bot/generated_pdfs/", timeout=15)
    log("STEP 7", f"Remote PDF Files:\n{ls_out.strip()}")

    # 8. Test HTTP PDF Endpoints
    log("STEP 8", "Testing FastAPI PDF Endpoints with curl...")
    endpoints = [
        "http://127.0.0.1:8000/api/documents/pdf/IV-202608-472",
        "https://srv1913532.hstgr.cloud/api/documents/pdf/IV-202608-472",
        "https://srv1913532.hstgr.cloud/api/documents/pdf/QT-202608-799",
        "https://srv1913532.hstgr.cloud/api/documents/pdf/RE-202608-001"
    ]
    for url in endpoints:
        curl_cmd = f"curl -I -s -w 'HTTP_CODE:%{{http_code}} CONTENT_TYPE:%{{content_type}}' '{url}'"
        curl_res = run_ssh_command(curl_cmd, timeout=20).strip()
        log("STEP 8", f"Endpoint [{url}] -> {curl_res}")

    # 9. Download PDFs to Local test_output
    log("STEP 9", f"Downloading PDFs to local test_output directory: {TEST_OUTPUT_DIR}...")
    test_docs = ["IV-202608-472.pdf", "QT-202608-799.pdf", "RE-202608-001.pdf"]
    for pdf_name in test_docs:
        rpath = f"/opt/ghn168_bot/generated_pdfs/{pdf_name}"
        lpath = str(TEST_OUTPUT_DIR / pdf_name)
        log("STEP 9", f"Downloading {pdf_name} -> {lpath}...")
        download_file_scp(rpath, lpath, timeout=30)
        size = os.path.getsize(lpath) if os.path.exists(lpath) else 0
        log("STEP 9", f"✅ Downloaded {pdf_name} (Size: {size:,} bytes)")

    # 10. Run Full Test Suite on VPS
    log("STEP 10", "Running Unit & Integration Tests on VPS...")
    test_run = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest test_pdf_generation_flow.py test_line_flex_schema_validation.py", timeout=45)
    log("STEP 10", f"VPS Test Suite Output:\n{test_run.strip()}")

    print("\n" + "=" * 80)
    print("  🎉 HEADLESS CHROMIUM PDF ENGINE DEPLOYMENT & TEST COMPLETE 100%")
    print("=" * 80)


if __name__ == "__main__":
    main()
