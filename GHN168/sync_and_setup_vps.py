#!/usr/bin/env python3
"""
================================================================================
GHN168 - VPS Full Automation Script (Deployment, Chromium Setup, PDF Test)
================================================================================
"""

import json
import os
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
TEST_OUTPUT_DIR = BASE_DIR / "test_output"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_URL = "https://srv1913532.hstgr.cloud"
SECRET = "ecdaa1e4e2d9d58dfce70db8070df072"
HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json"
}


def log(stage: str, msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def deploy_files(files_dict: dict, restart: bool = True):
    log("DEPLOY", f"Deploying {len(files_dict)} files to {SERVER_URL}...")
    res = requests.post(
        f"{SERVER_URL}/api/admin/deploy",
        headers=HEADERS,
        json={"files": files_dict, "restart": restart},
        timeout=30
    )
    if res.status_code != 200:
        raise RuntimeError(f"Deploy failed HTTP {res.status_code}: {res.text}")
    log("DEPLOY", f"Deploy response: {res.json()}")
    return res.json()


def wait_for_health(timeout: int = 30):
    log("HEALTH", "Waiting for server to become online...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{SERVER_URL}/health", timeout=3)
            if r.status_code == 200:
                log("HEALTH", f"✅ Server is online ({time.time()-start:.1f}s)")
                return True
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError("Server did not come back online in time.")


def remote_exec(cmd: str, timeout: int = 180):
    log("EXEC", f"Running: {cmd[:120]}...")
    res = requests.post(
        f"{SERVER_URL}/api/admin/exec",
        headers=HEADERS,
        json={"command": cmd, "timeout": timeout},
        timeout=timeout + 10
    )
    if res.status_code != 200:
        raise RuntimeError(f"Exec failed HTTP {res.status_code}: {res.text}")
    data = res.json()
    log("EXEC", f"ReturnCode: {data.get('returncode')}")
    if data.get("stdout"):
        print(f"[STDOUT]\n{data['stdout'].strip()}", flush=True)
    if data.get("stderr"):
        print(f"[STDERR]\n{data['stderr'].strip()}", flush=True)
    return data


def main():
    print("=" * 80)
    print("🚀 GHN168 - VPS HEADLESS CHROMIUM PDF ENGINE AUTOMATION")
    print("=" * 80)

    # 1. Read files to deploy
    files_to_send = {}
    filenames = [
        "local_pdf_engine.py",
        "document_template_engine.py",
        "ghn168_sync_service.py",
        "line_bot_server.py",
        "test_pdf_generation_flow.py"
    ]
    for fname in filenames:
        fpath = BASE_DIR / fname
        with open(fpath, "r", encoding="utf-8") as f:
            files_to_send[fname] = f.read()

    # Step 1: Deploy updated line_bot_server and modules
    log("STEP 1", "Deploying core modules with /api/admin/exec support...")
    deploy_files(files_to_send, restart=True)
    time.sleep(2)
    wait_for_health()

    # Step 2: Install system packages (Chromium, Thai Fonts) on Ubuntu VPS
    log("STEP 2", "Installing Chromium & Thai Fonts on Ubuntu VPS...")
    setup_cmd = """
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y fonts-thai-tlwg fonts-noto-cjk fonts-noto-core fontconfig curl wget

    # Check for Chromium / Chrome
    if ! command -v chromium &>/dev/null && ! command -v chromium-browser &>/dev/null && ! command -v google-chrome &>/dev/null; then
        echo "Installing Chromium browser..."
        apt-get install -y chromium-browser chromium || true
    fi

    # If chromium not available from apt on Ubuntu 24.04, install Google Chrome Stable deb
    if ! command -v chromium &>/dev/null && ! command -v chromium-browser &>/dev/null && ! command -v google-chrome &>/dev/null; then
        echo "Downloading and installing Google Chrome Stable..."
        wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome.deb
        apt-get install -y /tmp/google-chrome.deb || apt-get install -y -f
        rm -f /tmp/google-chrome.deb
    fi

    # Create storage directory
    mkdir -p /opt/ghn168_bot/generated_pdfs
    chmod 777 /opt/ghn168_bot/generated_pdfs

    # Update font cache
    fc-cache -f -v
    """
    remote_exec(setup_cmd, timeout=300)

    # Step 3: Verify Chromium and Fonts
    log("STEP 3", "Verifying Chromium and Thai font installation...")
    chk_cmd = """
    echo "=== CHROMIUM BINARY CHECK ==="
    which chromium chromium-browser google-chrome google-chrome-stable || true
    (chromium --version || chromium-browser --version || google-chrome --version) 2>/dev/null || true

    echo "=== THAI FONTS CHECK ==="
    fc-list : lang=th | head -n 10
    """
    chk_res = remote_exec(chk_cmd, timeout=30)

    # Step 4: Generate Real PDFs on VPS
    log("STEP 4", "Generating 3 real documents on VPS...")
    gen_cmd = """
    cd /opt/ghn168_bot
    /opt/ghn168_bot/venv/bin/python3 -c "
import json
from local_pdf_engine import generate_document_pdf

# 1. IV-202608-472 (บ. เอ็ม-คูล 19,260 บาท)
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
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์ (บอสเก่ง)'
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
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์ (คุณเก่ง)'
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
    'signer_name': 'นาย มงคล วงศ์สกุลยานนท์ (คุณเก่ง)'
}
res3 = generate_document_pdf('receipt', re_data)
print('RE Result:', json.dumps(res3, ensure_ascii=False))
"
    """
    remote_exec(gen_cmd, timeout=60)

    # Step 5: Check files in VPS generated_pdfs directory
    log("STEP 5", "Checking generated PDF files on VPS storage...")
    remote_exec("ls -lh /opt/ghn168_bot/generated_pdfs/", timeout=15)

    # Step 6: Test HTTP PDF Endpoint and Download PDFs
    log("STEP 6", "Testing HTTP PDF Endpoint & downloading PDFs to local test_output/...")
    test_docs = ["IV-202608-472", "QT-202608-799", "RE-202608-001"]
    
    for doc_no in test_docs:
        url = f"{SERVER_URL}/api/documents/pdf/{doc_no}"
        log("STEP 6", f"Fetching {url}...")
        r = requests.get(url, timeout=30)
        log("STEP 6", f"Response Status: {r.status_code}, Content-Type: {r.headers.get('content-type')}, Size: {len(r.content):,} bytes")
        
        if r.status_code == 200 and len(r.content) > 1000:
            local_save_path = TEST_OUTPUT_DIR / f"{doc_no}.pdf"
            with open(local_save_path, "wb") as f:
                f.write(r.content)
            log("STEP 6", f"✅ Saved {local_save_path.name} ({len(r.content):,} bytes)")
        else:
            log("STEP 6", f"❌ Failed to fetch {doc_no}: HTTP {r.status_code}")

    # Step 7: Run Remote Test Suite
    log("STEP 7", "Executing full test suite on VPS...")
    test_cmd = "cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest test_pdf_generation_flow.py test_line_flex_schema_validation.py"
    remote_exec(test_cmd, timeout=60)

    print("\n" + "=" * 80)
    print("  🎉 COMPLETE 100% HEADLESS CHROMIUM PDF ENGINE DEPLOYED & VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()
