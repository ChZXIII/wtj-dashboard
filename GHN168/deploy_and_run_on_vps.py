#!/usr/bin/env python3
"""
================================================================================
GHN168 - VPS Deploy & Google Sheets Live Repair Runner
================================================================================
Author: Q (Lead Backend Developer, ChZ Agent Corp)
Target: 187.127.118.19 (srv1913532.hstgr.cloud)
"""

import os
import sys
import time
import pexpect

VPS_HOST = "187.127.118.19"
VPS_USER = "root"
VPS_PASS = "ziqheV-gacsij-tedxy6"
REMOTE_APP_DIR = "/opt/ghn168_bot"

SSH_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=15"
]


def run_ssh_command(cmd: str, timeout: int = 60) -> str:
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {VPS_USER}@{VPS_HOST} '{cmd}'"
    child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding="utf-8")
    
    prompts = [
        r"[pP]assword:",
        r"Are you sure you want to continue connecting \(yes/no.*\)\?",
        pexpect.EOF,
        pexpect.TIMEOUT
    ]
    
    output = []
    while True:
        idx = child.expect(prompts, timeout=timeout)
        if idx == 0:
            child.sendline(VPS_PASS)
            break
        elif idx == 1:
            child.sendline("yes")
        elif idx == 2:
            return child.before or ""
        elif idx == 3:
            raise TimeoutError(f"Timeout connecting to VPS: {cmd}")

    try:
        while True:
            line = child.readline()
            if not line:
                break
            print(line, end="", flush=True)
            output.append(line)
    except (pexpect.EOF, pexpect.TIMEOUT):
        pass
    
    return "".join(output)


def scp_file(local_path: str, remote_path: str, timeout: int = 60):
    scp_cmd = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {local_path} {VPS_USER}@{VPS_HOST}:{remote_path}"
    child = pexpect.spawn(scp_cmd, timeout=timeout, encoding="utf-8")
    
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
            return
        elif idx == 3:
            raise TimeoutError(f"Timeout uploading file {local_path}")
            
    child.expect(pexpect.EOF)


def main():
    print("=" * 80)
    print("🚀 [Step 1] Uploading updated files to VPS...")
    print("=" * 80)
    
    files_to_upload = [
        "ghn168_sync_service.py",
        "repair_sheet_tax_ids_and_duplicates.py"
    ]
    
    for f in files_to_upload:
        local_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), f)
        remote_p = f"{REMOTE_APP_DIR}/{f}"
        print(f"  • Uploading {f} -> {remote_p} ...")
        scp_file(local_p, remote_p)
        print(f"  ✅ Uploaded {f}")

    print("\n" + "=" * 80)
    print("🚀 [Step 2] Executing repair_sheet_tax_ids_and_duplicates.py on VPS...")
    print("=" * 80)
    
    repair_output = run_ssh_command(f"cd {REMOTE_APP_DIR} && python3 repair_sheet_tax_ids_and_duplicates.py", timeout=120)
    print(repair_output)

    print("\n" + "=" * 80)
    print("🚀 [Step 3] Restarting ghn168-bot service on VPS...")
    print("=" * 80)
    run_ssh_command("systemctl restart ghn168-bot", timeout=30)
    time.sleep(3)
    
    print("\n" + "=" * 80)
    print("🚀 [Step 4] Checking service status and health...")
    print("=" * 80)
    status_out = run_ssh_command("systemctl status ghn168-bot --no-pager -n 15", timeout=30)
    print(status_out)
    
    health_out = run_ssh_command("curl -s http://127.0.0.1:8000/health", timeout=15)
    print("Health check response:", health_out)


if __name__ == "__main__":
    main()
