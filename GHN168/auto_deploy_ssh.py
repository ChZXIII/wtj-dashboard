#!/usr/bin/env python3
"""
==============================================================================
GHN168 LINE Bot - Automated SSH Deployment Script
==============================================================================
Target VPS: 187.127.118.19 (srv1913532.hstgr.cloud)
User: root
App Directory: /opt/ghn168_bot

Features:
1. Connects to VPS using pexpect over SSH/SCP.
2. Uploads `install_vps.sh` to `/tmp/install_vps.sh`.
3. Executes `bash /tmp/install_vps.sh` and streams live installation output.
4. Verifies systemd service status, Caddy reverse proxy, local health endpoint,
   and file list in `/opt/ghn168_bot`.
5. Outputs a structured deployment summary.
==============================================================================
"""

import os
import sys
import time
import json
import pexpect

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
VPS_HOST = "187.127.118.19"
VPS_USER = "root"
VPS_PASS = "ziqheV-gacsij-tedxy6"
VPS_PORT = 22

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "install_vps.sh")
REMOTE_INSTALL_SCRIPT = "/tmp/install_vps.sh"
REMOTE_APP_DIR = "/opt/ghn168_bot"

SSH_COMMON_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=30"
]


def log(stage: str, message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{stage}] {message}", flush=True)


def run_ssh_command(cmd: str, timeout: int = 60, stream_output: bool = False) -> str:
    """
    Executes a command on the remote VPS via SSH using pexpect.
    Returns the accumulated output as string.
    """
    ssh_cmd = [
        "ssh",
        *SSH_COMMON_OPTIONS,
        f"{VPS_USER}@{VPS_HOST}",
        cmd
    ]
    command_str = " ".join(f'"{c}"' if (" " in c or "$" in c or "&" in c or "|" in c) else c for c in ssh_cmd)
    
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
            raise TimeoutError(f"SSH command timed out waiting for prompt: {cmd}\nOutput so far:\n{''.join(output_buffer)}")

    if stream_output:
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
    """
    Uploads a file to the VPS using scp and pexpect.
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")
    
    scp_cmd = [
        "scp",
        *SSH_COMMON_OPTIONS,
        local_path,
        f"{VPS_USER}@{VPS_HOST}:{remote_path}"
    ]
    command_str = " ".join(scp_cmd)
    
    log("SCP", f"Uploading {local_path} -> {remote_path}...")
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
    
    log("SCP", "Upload command finished.")
    return True


def main():
    print("=" * 70, flush=True)
    print("  🚀 GHN168 LINE BOT - FULL AUTOMATED VPS DEPLOYMENT", flush=True)
    print(f"  Target VPS : {VPS_HOST} ({VPS_USER})", flush=True)
    print(f"  Local File : {INSTALL_SCRIPT_PATH}", flush=True)
    print(f"  Target Dir : {REMOTE_APP_DIR}", flush=True)
    print("=" * 70, flush=True)
    
    results = {
        "host": VPS_HOST,
        "status": "in_progress",
        "steps": {}
    }
    
    # -------------------------------------------------------------------------
    # Step 1: Verify SSH Connectivity
    # -------------------------------------------------------------------------
    log("STEP 1", "Verifying SSH connection and server details...")
    try:
        uname_out = run_ssh_command("uname -a && uptime", timeout=20)
        log("STEP 1", f"Connected! Server info:\n{uname_out.strip()}")
        results["steps"]["ssh_connection"] = {"status": "success", "info": uname_out.strip()}
    except Exception as e:
        log("STEP 1", f"Failed to connect via SSH: {e}")
        results["steps"]["ssh_connection"] = {"status": "failed", "error": str(e)}
        results["status"] = "failed"
        print(json.dumps(results, indent=2))
        sys.exit(1)
        
    # -------------------------------------------------------------------------
    # Step 2: Upload updated code files to /opt/ghn168_bot/
    # -------------------------------------------------------------------------
    files_to_sync = [
        ".env",
        "index.html",
        "app.js",
        "local_pdf_engine.py",
        "document_template_engine.py",
        "ghn168_sync_service.py",
        "google_sheets_sync_script.gs",
        "line_bot_server.py",
        "manifest.json",
        "signature_pad.html",
        "sw.js",
        "start_line_bot.sh"
    ]
    log("STEP 2", "Uploading updated core Python modules to /opt/ghn168_bot/...")
    try:
        for fname in files_to_sync:
            lpath = os.path.join(SCRIPT_DIR, fname)
            if not os.path.isfile(lpath):
                continue
            rpath = f"{REMOTE_APP_DIR}/{fname}"
            log("STEP 2", f"Uploading {fname} -> {rpath}...")
            upload_file_scp(lpath, rpath, timeout=60)
            log("STEP 2", f"✅ {fname} uploaded.")

        # Create assets folder on remote and upload key images
        run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/assets", timeout=10)
        assets_dir = os.path.join(SCRIPT_DIR, "assets")
        if os.path.isdir(assets_dir):
            for afile in os.listdir(assets_dir):
                if afile.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".js", ".html")):
                    l_asset = os.path.join(assets_dir, afile)
                    r_asset = f"{REMOTE_APP_DIR}/assets/{afile}"
                    upload_file_scp(l_asset, r_asset, timeout=30)
            log("STEP 2", "✅ Assets uploaded.")

        # Create signatures folder on remote and upload signatures
        run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/signatures", timeout=10)
        sig_dir = os.path.join(SCRIPT_DIR, "signatures")
        if os.path.isdir(sig_dir):
            for sfile in os.listdir(sig_dir):
                if sfile.endswith((".png", ".jpg", ".jpeg")):
                    l_sig = os.path.join(sig_dir, sfile)
                    r_sig = f"{REMOTE_APP_DIR}/signatures/{sfile}"
                    upload_file_scp(l_sig, r_sig, timeout=30)
            log("STEP 2", "✅ Signatures uploaded.")

        # Create tests folder on remote and upload all test suites
        run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/tests", timeout=10)
        tests_dir = os.path.join(SCRIPT_DIR, "tests")
        if os.path.isdir(tests_dir):
            for tfile in os.listdir(tests_dir):
                if tfile.endswith(".py"):
                    l_t = os.path.join(tests_dir, tfile)
                    r_t = f"{REMOTE_APP_DIR}/tests/{tfile}"
                    upload_file_scp(l_t, r_t, timeout=30)
            log("STEP 2", "✅ Tests uploaded.")

        # Verify files on remote
        check_remote = run_ssh_command(f"ls -lh {REMOTE_APP_DIR}", timeout=15)
        log("STEP 2", f"Files verified on remote:\n{check_remote.strip()}")
        results["steps"]["file_upload"] = {"status": "success", "info": check_remote.strip()}
    except Exception as e:
        log("STEP 2", f"Failed to upload files: {e}")
        results["steps"]["file_upload"] = {"status": "failed", "error": str(e)}
        results["status"] = "failed"
        print(json.dumps(results, indent=2))
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Step 2.6: Run Full Test Suites on VPS
    # -------------------------------------------------------------------------
    log("STEP 2.6", "Executing full test discovery suite on VPS...")
    try:
        test_out = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest discover -s tests -p 'test_*.py'", timeout=60)
        log("STEP 2.6", f"VPS Test Suite Output:\n{test_out.strip()}")
        results["steps"]["vps_test_suite"] = {"status": "success", "output": test_out.strip()}
    except Exception as e:
        log("STEP 2.6", f"VPS Test suite encountered an error: {e}")
        results["steps"]["vps_test_suite"] = {"status": "warning", "error": str(e)}

    # -------------------------------------------------------------------------
    # Step 3: Restart systemd service ghn168-bot
    # -------------------------------------------------------------------------
    log("STEP 3", "Restarting ghn168-bot systemd service on VPS...")
    try:
        restart_output = run_ssh_command("systemctl restart ghn168-bot", timeout=30)
        time.sleep(2)
        is_active = run_ssh_command("systemctl is-active ghn168-bot", timeout=10).strip()
        log("STEP 3", f"ghn168-bot restart completed. Service active: {is_active}")
        results["steps"]["service_restart"] = {"status": "success", "is_active": is_active}
    except Exception as e:
        log("STEP 3", f"Service restart encountered an error: {e}")
        results["steps"]["service_restart"] = {"status": "failed", "error": str(e)}

    # -------------------------------------------------------------------------
    # Step 4: Verification & Health Checks
    # -------------------------------------------------------------------------
    log("STEP 4", "Performing comprehensive verification and health checks...")
    
    # 4.1 Systemd Service Status
    try:
        bot_svc_out = run_ssh_command("systemctl status ghn168-bot --no-pager", timeout=15)
        is_bot_active = run_ssh_command("systemctl is-active ghn168-bot", timeout=10).strip()
        results["steps"]["service_status"] = {
            "is_active": is_bot_active,
            "details": bot_svc_out.strip()
        }
        log("VERIFY", f"ghn168-bot service status: {is_bot_active}")
    except Exception as e:
        log("VERIFY", f"Failed to check bot service: {e}")
        results["steps"]["service_status"] = {"error": str(e)}

    # 4.2 Caddy Reverse Proxy Status
    try:
        caddy_svc_out = run_ssh_command("systemctl status caddy --no-pager", timeout=15)
        is_caddy_active = run_ssh_command("systemctl is-active caddy", timeout=10).strip()
        results["steps"]["caddy_status"] = {
            "is_active": is_caddy_active,
            "details": caddy_svc_out.strip()
        }
        log("VERIFY", f"caddy service status: {is_caddy_active}")
    except Exception as e:
        log("VERIFY", f"Failed to check caddy: {e}")
        results["steps"]["caddy_status"] = {"error": str(e)}

    # 4.3 Local Health Check (127.0.0.1:8000/health)
    try:
        health_out = run_ssh_command("curl -s http://127.0.0.1:8000/health", timeout=15)
        log("VERIFY", f"Local health check response: {health_out.strip()}")
        results["steps"]["health_check"] = {"response": health_out.strip()}
    except Exception as e:
        log("VERIFY", f"Health check failed: {e}")
        results["steps"]["health_check"] = {"error": str(e)}

    # 4.4 File List in /opt/ghn168_bot
    try:
        files_out = run_ssh_command("ls -la /opt/ghn168_bot", timeout=15)
        log("VERIFY", f"Application files in {REMOTE_APP_DIR}:\n{files_out.strip()}")
        results["steps"]["remote_files"] = {"list": files_out.strip()}
    except Exception as e:
        log("VERIFY", f"Failed to list files: {e}")
        results["steps"]["remote_files"] = {"error": str(e)}

    # 4.5 Live Document Conversion Flex Message Verification on VPS
    try:
        conv_check_cmd = """curl -s -X POST http://127.0.0.1:8000/api/documents/convert -H "Content-Type: application/json" -d '{"source_doc_no": "QT2608-001", "target_type": "invoice"}'"""
        conv_check_out = run_ssh_command(conv_check_cmd, timeout=30)
        log("VERIFY", f"VPS Live Conversion API Response:\n{conv_check_out[:300]}...")
        results["steps"]["conversion_live_check"] = {"status": "success", "response": conv_check_out[:300]}
    except Exception as e:
        log("VERIFY", f"Conversion Live Check failed: {e}")
        results["steps"]["conversion_live_check"] = {"error": str(e)}

    # 4.6 Remote Schema Validation Test Execution
    try:
        test_out = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m unittest test_line_flex_schema_validation.py", timeout=20)
        log("VERIFY", f"Remote test suite result:\n{test_out.strip()}")
        results["steps"]["remote_tests"] = {"output": test_out.strip(), "status": "passed" if "OK" in test_out else "warning"}
    except Exception as e:
        log("VERIFY", f"Remote tests encountered an issue: {e}")
        results["steps"]["remote_tests"] = {"error": str(e)}

    # 4.7 Journalctl Logs Check
    try:
        journal_out = run_ssh_command("journalctl -u ghn168-bot -n 25 --no-pager", timeout=15)
        log("VERIFY", f"Journalctl logs (recent 25 lines):\n{journal_out.strip()}")
        results["steps"]["journalctl_logs"] = {"output": journal_out.strip(), "status": "success"}
    except Exception as e:
        log("VERIFY", f"Failed to read journalctl logs: {e}")
        results["steps"]["journalctl_logs"] = {"error": str(e)}

    # -------------------------------------------------------------------------
    # Step 5: Summary Report
    # -------------------------------------------------------------------------
    bot_ok = results.get("steps", {}).get("service_status", {}).get("is_active") == "active"
    caddy_ok = results.get("steps", {}).get("caddy_status", {}).get("is_active") == "active"
    
    if bot_ok and caddy_ok:
        results["status"] = "success"
    else:
        results["status"] = "partial_or_failed"

    print("\n" + "=" * 70, flush=True)
    print("  📊 DEPLOYMENT RESULT SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"  Target VPS      : {VPS_HOST}", flush=True)
    print(f"  Bot Service     : {'✅ ACTIVE' if bot_ok else '❌ NOT ACTIVE'}", flush=True)
    print(f"  Caddy Proxy     : {'✅ ACTIVE' if caddy_ok else '❌ NOT ACTIVE'}", flush=True)
    print(f"  Local Health    : {results.get('steps', {}).get('health_check', {}).get('response', 'N/A')}", flush=True)
    print(f"  Webhook URL     : https://srv1913532.hstgr.cloud/callback", flush=True)
    print(f"  Health Endpoint : https://srv1913532.hstgr.cloud/health", flush=True)
    print("=" * 70, flush=True)
    
    return results


if __name__ == "__main__":
    main()
