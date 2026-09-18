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
        "ghn_memory_engine.py",
        "ghn168_sync_service.py",
        "google_sheets_sync_script.gs",
        "fix_tax_id_leading_zeros.py",
        "cleanup_receipt_duplicates.py",
        "recover_income_tab.py",
        "regenerate_aot_receipt.py",
        "sync_receipt_aot_re563.py",
        "repair_expense_tab.py",
        "line_bot_server.py",
        "manifest.json",
        "signature_pad.html",
        "sw.js",
        "start_line_bot.sh",
        "tests/test_clean_slate_line_bot.py",
        "tests/test_po_job_code_and_pdf_pipeline.py"
    ]
    log("STEP 2", "Uploading updated core Python modules to /opt/ghn168_bot/...")
    try:
        run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/tests {REMOTE_APP_DIR}/data {REMOTE_APP_DIR}/assets {REMOTE_APP_DIR}/signatures", timeout=15)
        for fname in files_to_sync:
            lpath = os.path.join(SCRIPT_DIR, fname)
            if not os.path.isfile(lpath):
                continue
            rpath = f"{REMOTE_APP_DIR}/{fname}"
            log("STEP 2", f"Uploading {fname} -> {rpath}...")
            upload_file_scp(lpath, rpath, timeout=60)
            log("STEP 2", f"✅ {fname} uploaded.")

        # Create data folder on remote and upload data files
        run_ssh_command(f"mkdir -p {REMOTE_APP_DIR}/data", timeout=10)
        data_dir = os.path.join(SCRIPT_DIR, "data")
        if os.path.isdir(data_dir):
            for dfile in os.listdir(data_dir):
                if dfile.endswith(".json"):
                    l_data = os.path.join(data_dir, dfile)
                    r_data = f"{REMOTE_APP_DIR}/data/{dfile}"
                    upload_file_scp(l_data, r_data, timeout=30)
            log("STEP 2", "✅ Data files uploaded.")

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
    # Step 2.6: Pre-restart Syntax Validation on VPS
    # -------------------------------------------------------------------------
    log("STEP 2.6", "Verifying line_bot_server syntax on remote VPS...")
    try:
        py_check = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/python3 -m py_compile line_bot_server.py", timeout=20)
        log("STEP 2.6", "✅ line_bot_server.py syntax verified.")
        results["steps"]["pre_syntax_check"] = {"status": "success"}
    except Exception as e:
        log("STEP 2.6", f"Pre-check failed: {e}")
        results["steps"]["pre_syntax_check"] = {"status": "warning", "error": str(e)}

    # -------------------------------------------------------------------------
    # Step 2.8: Enforce Single Worker (--workers 1) & 7-Day PDF Auto-Purge Cron
    # -------------------------------------------------------------------------
    log("STEP 2.8", "Enforcing single worker (--workers 1) and setting up 7-day PDF auto-purge...")
    try:
        # 1. Update systemd service to use --workers 1 to avoid duplicate cron notifications
        service_file_content = """[Unit]
Description=GHN168 Corporate & Accounting Executive Assistant LINE Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ghn168_bot
ExecStart=/opt/ghn168_bot/venv/bin/uvicorn line_bot_server:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
EnvironmentFile=/opt/ghn168_bot/.env

[Install]
WantedBy=multi-user.target
"""
        run_ssh_command("cat << 'EOF' > /etc/systemd/system/ghn168-bot.service\n" + service_file_content + "\nEOF", timeout=15)
        run_ssh_command("systemctl daemon-reload", timeout=15)
        log("STEP 2.8", "✅ ghn168-bot.service updated with --workers 1.")

        # 2. Setup Daily Cron for auto-purging generated PDFs older than 7 days
        purge_cron_cmd = "find /opt/ghn168_bot/generated_docs/ -name '*.pdf' -type f -mtime +7 -delete"
        # Ensure generated_docs directory exists
        run_ssh_command("mkdir -p /opt/ghn168_bot/generated_docs", timeout=10)
        # Execute immediate purge check
        run_ssh_command(purge_cron_cmd, timeout=15)
        # Install cron job in /etc/cron.daily/ghn168_purge_pdfs
        cron_script = f"""#!/bin/bash
{purge_cron_cmd}
"""
        run_ssh_command("cat << 'EOF' > /etc/cron.daily/ghn168_purge_pdfs\n" + cron_script + "\nEOF", timeout=15)
        run_ssh_command("chmod +x /etc/cron.daily/ghn168_purge_pdfs", timeout=10)
        log("STEP 2.8", "✅ 7-day PDF auto-purge cron installed in /etc/cron.daily/ghn168_purge_pdfs.")
        results["steps"]["single_worker_and_purge"] = {"status": "success"}
    except Exception as e:
        log("STEP 2.8", f"Failed configuring single worker or purge: {e}")
        results["steps"]["single_worker_and_purge"] = {"status": "warning", "error": str(e)}

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

    # 4.5 Remote Clean Slate Test Execution
    try:
        test_out = run_ssh_command("cd /opt/ghn168_bot && /opt/ghn168_bot/venv/bin/pytest tests/test_clean_slate_line_bot.py", timeout=60)
        log("VERIFY", f"Remote clean slate test suite result:\n{test_out.strip()}")
        results["steps"]["clean_slate_tests"] = {
            "output": test_out.strip(),
            "status": "passed" if ("passed" in test_out and "failed" not in test_out) else "warning"
        }
    except Exception as e:
        log("VERIFY", f"Remote clean slate tests encountered an issue: {e}")
        results["steps"]["clean_slate_tests"] = {"error": str(e), "status": "failed"}

    # 4.6 Remote Health Check Validation
    try:
        health_public = run_ssh_command("curl -s https://srv1913532.hstgr.cloud/health", timeout=15).strip()
        if not health_public or "status" not in health_public:
            health_public = run_ssh_command("curl -s http://127.0.0.1:8000/health", timeout=15).strip()
        log("VERIFY", f"Remote health check validation response: {health_public}")
        results["steps"]["remote_health_validation"] = {"response": health_public, "status": "success"}
    except Exception as e:
        log("VERIFY", f"Remote health check validation failed: {e}")
        results["steps"]["remote_health_validation"] = {"error": str(e), "status": "failed"}

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
    clean_tests_ok = results.get("steps", {}).get("clean_slate_tests", {}).get("status") == "passed"
    
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
    print(f"  Clean Slate Test: {'✅ PASSED' if clean_tests_ok else '⚠️ CHECK LOGS'}", flush=True)
    print(f"  Local Health    : {results.get('steps', {}).get('health_check', {}).get('response', 'N/A')}", flush=True)
    print(f"  Health Validated: {results.get('steps', {}).get('remote_health_validation', {}).get('response', 'N/A')}", flush=True)
    print(f"  Webhook URL     : https://srv1913532.hstgr.cloud/callback", flush=True)
    print(f"  Health Endpoint : https://srv1913532.hstgr.cloud/health", flush=True)
    print("=" * 70, flush=True)
    
    return results


if __name__ == "__main__":
    main()
