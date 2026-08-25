#!/usr/bin/env python3
"""
Install native Google Chrome Stable deb on Ubuntu VPS to bypass snap confinement.
"""
import requests
import json
import time

SERVER_URL = "https://srv1913532.hstgr.cloud"
SECRET = "ecdaa1e4e2d9d58dfce70db8070df072"
HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json"
}

def remote_exec(cmd: str, timeout: int = 180):
    print(f"[EXEC] {cmd[:100]}...", flush=True)
    res = requests.post(
        f"{SERVER_URL}/api/admin/exec",
        headers=HEADERS,
        json={"command": cmd, "timeout": timeout},
        timeout=timeout + 10
    )
    data = res.json()
    print(f"ReturnCode: {data.get('returncode')}")
    if data.get("stdout"):
        print(f"[STDOUT]\n{data['stdout'].strip()}", flush=True)
    if data.get("stderr"):
        print(f"[STDERR]\n{data['stderr'].strip()}", flush=True)
    return data

def main():
    print("--> 1. Downloading and installing Google Chrome Stable (.deb)...")
    cmd = """
    export DEBIAN_FRONTEND=noninteractive
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome-stable.deb
    dpkg -i /tmp/google-chrome-stable.deb || apt-get install -y -f
    rm -f /tmp/google-chrome-stable.deb
    which google-chrome google-chrome-stable chromium
    google-chrome --version
    """
    remote_exec(cmd, timeout=120)

if __name__ == "__main__":
    main()
