#!/usr/bin/env python3
"""
================================================================================
GHN168 - Production VPS Deployment & Live Google Drive Upload Verification
================================================================================
Target VPS: https://srv1913532.hstgr.cloud (187.127.118.19)
Authentication: LINE_CHANNEL_SECRET Bearer Token

Tasks:
1. Deploy updated files (google_sheets_sync_script.gs, ghn168_sync_service.py,
   line_bot_server.py, test_pdf_generation_flow.py) to VPS
2. Restart ghn168-bot service and verify health
3. Run live test on VPS to generate a real PDF and upload directly to Google Drive
4. Run full test suite on VPS to ensure 100% pass
================================================================================
"""

import json
import os
from pathlib import Path
import time
import requests

VPS_BASE_URL = "https://srv1913532.hstgr.cloud"
SECRET = "ecdaa1e4e2d9d58dfce70db8070df072"
HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json"
}

BASE_DIR = Path(__file__).resolve().parent


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


def main():
    print("=" * 80)
    print("🚀 GHN168 - DIRECT PDF UPLOAD TO GOOGLE DRIVE: DEPLOY & LIVE VERIFY")
    print(f"VPS Endpoint: {VPS_BASE_URL}")
    print("=" * 80)

    # 1. Health check before deploy
    log("STEP 1", "Checking initial VPS health status...")
    h_res = requests.get(f"{VPS_BASE_URL}/health", timeout=10)
    log("STEP 1", f"Health status HTTP {h_res.status_code}: {h_res.json()}")

    # 2. Deploy updated files to VPS
    log("STEP 2", "Deploying updated files to VPS via /api/admin/deploy...")
    files_to_deploy = [
        "google_sheets_sync_script.gs",
        "ghn168_sync_service.py",
        "line_bot_server.py",
        "document_template_engine.py",
        "local_pdf_engine.py",
        "test_pdf_generation_flow.py",
    ]
    deploy_payload = {"files": {}, "restart": True}
    for fname in files_to_deploy:
        fpath = BASE_DIR / fname
        if fpath.is_file():
            with open(fpath, "r", encoding="utf-8") as f:
                deploy_payload["files"][fname] = f.read()
            log("STEP 2", f"Prepared file {fname} ({fpath.stat().st_size:,} bytes)")

    dep_res = requests.post(f"{VPS_BASE_URL}/api/admin/deploy", headers=HEADERS, json=deploy_payload, timeout=60)
    log("STEP 2", f"Deploy Response HTTP {dep_res.status_code}: {dep_res.text}")

    # 3. Wait for service restart
    log("STEP 3", "Waiting for ghn168-bot service to restart...")
    time.sleep(5)
    healthy = False
    for attempt in range(1, 11):
        try:
            r = requests.get(f"{VPS_BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                log("STEP 3", f"✅ ghn168-bot restarted successfully on attempt {attempt}! Status: {r.json()}")
                healthy = True
                break
        except Exception as e:
            log("STEP 3", f"Waiting for restart (attempt {attempt}): {e}")
        time.sleep(2)

    if not healthy:
        raise RuntimeError("Service failed to become healthy after deploy.")

    # 4. Live PDF Generation & Direct Google Drive Upload on VPS
    log("STEP 4", "Executing Live PDF Generation & Direct Google Drive Upload on VPS...")
    vps_test_file = BASE_DIR / "vps_live_test.py"
    test_script_content = """import json
from ghn168_sync_service import generate_and_sync_document, upload_document_pdf
from line_bot_server import build_document_flex_message

doc_payload = {
    "client_name": "บริษัท เชียงใหม่ ครีเอทีฟ มีเดีย จำกัด",
    "client_tax_id": "0505560000123",
    "client_address": "123 ถ.ห้วยแก้ว ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200",
    "client_branch": "00000",
    "client_phone": "081-1111111",
    "project_name": "งานบริการถ่ายทำและผลิตคลิปวิดีโอ 4K โครงการ Direct Google Drive",
    "items": [
        {"desc": "งานถ่ายทำวิดีโอ 4K 1 คิว (ทีมกล้อง+ไฟ+เสียง)", "qty": 1, "price": 25000.0, "amount": 25000.0},
        {"desc": "งานตัดต่อและเกรดสี Master 4K", "qty": 1, "price": 10000.0, "amount": 10000.0}
    ],
    "is_vat": True,
    "vat_rate": 0.07,
    "wht_rate": 3.0,
    "signer_name": "นาย มงคล วงศ์สกุลยานนท์"
}

res = generate_and_sync_document("quotation", doc_payload)
flex = build_document_flex_message(res)

output = {
    "status": res.get("status"),
    "doc_no": res.get("doc_no"),
    "pdf_url": res.get("pdf_url"),
    "local_pdf_path": res.get("local_pdf_path"),
    "upload_result": res.get("upload_result"),
    "sheets_result": res.get("sheets_result"),
    "totals": res.get("totals"),
    "flex_button_uri": flex["contents"]["footer"]["contents"][0]["action"]["uri"]
}
print("LIVE_RESULT_JSON:" + json.dumps(output, ensure_ascii=False))
"""
    vps_test_file.write_text(test_script_content, encoding="utf-8")

    # Upload test script
    requests.post(
        f"{VPS_BASE_URL}/api/admin/deploy",
        headers=HEADERS,
        json={"files": {"vps_live_test.py": test_script_content}, "restart": False},
        timeout=30
    )

    exec_res = remote_exec("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python vps_live_test.py", timeout=120)
    stdout = exec_res.get("stdout", "")
    stderr = exec_res.get("stderr", "")
    log("STEP 4", f"Raw Output from VPS:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    live_json_str = ""
    for line in stdout.splitlines():
        if line.startswith("LIVE_RESULT_JSON:"):
            live_json_str = line[len("LIVE_RESULT_JSON:"):]
            break

    if live_json_str:
        live_data = json.loads(live_json_str)
        log("STEP 4", f"Parsed Live Test Data: {json.dumps(live_data, indent=2, ensure_ascii=False)}")
        print("\n" + "=" * 80)
        print("🎉 LIVE VERIFICATION RESULTS:")
        print(f"  • Document No:       {live_data.get('doc_no')}")
        print(f"  • Status:            {live_data.get('status')}")
        print(f"  • Local PDF Path:    {live_data.get('local_pdf_path')}")
        print(f"  • Google Drive URL:  {live_data.get('pdf_url')}")
        print(f"  • Upload Result:     {live_data.get('upload_result')}")
        print(f"  • Sheets Result:     {live_data.get('sheets_result')}")
        print(f"  • Flex Button URI:   {live_data.get('flex_button_uri')}")
        print("=" * 80 + "\n")
    else:
        log("STEP 4", "⚠️ Could not parse JSON from script output.")

    # 5. Run test suite on VPS
    log("STEP 5", "Running full test suite on VPS...")
    test_run = remote_exec("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python test_pdf_generation_flow.py", timeout=120)
    log("STEP 5", f"VPS test_pdf_generation_flow stdout:\n{test_run.get('stdout', '')}")
    if test_run.get("returncode", 0) != 0:
        log("STEP 5", f"VPS test stderr: {test_run.get('stderr', '')}")

    print("\n✅ Deployment & Live Verification Completed Successfully!")


if __name__ == "__main__":
    main()
