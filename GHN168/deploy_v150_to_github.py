#!/usr/bin/env python3
"""
deploy_v150_to_github.py
========================
Automated Deployment Script for GHN168 v1.50
Author: Q (น้องคิว) Senior Backend Developer - ChZ Agent Corp

Functions:
1. Verify v1.50 bump in index.html & sw.js
2. Copy production web files & assets to ChZ_Room/GHN168/
3. Stage, commit, and push to GitHub origin main
"""

import sys
import shutil
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path("/Users/chz/Desktop/ChZ_Agent_Corp")
GHN_DIR = REPO_ROOT / "GHN168"
CHZ_ROOM_GHN_DIR = REPO_ROOT / "ChZ_Room" / "GHN168"

COMMIT_MESSAGE = (
    "feat(GHN168): v1.50 Dual-engine PDF & Drive upload, "
    "13-digit Tax ID formatting, Real-time numbering & duplicate guard"
)

SYNC_FILES = [
    "index.html",
    "app.js",
    "sw.js",
    "manifest.json",
    "vercel.json",
    "signature_pad.html",
    "google_sheets_sync_script.gs",
    "README.md",
]

SYNC_DIRS = [
    "assets",
    "signatures",
]


def log(msg: str, status: str = "INFO"):
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "WARN": "⚠️", "ERROR": "❌", "STEP": "🚀"}
    icon = icons.get(status, "🔹")
    print(f"{icon} [{status}] {msg}")


def run_cmd(cmd: list, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    log(f"Running: {' '.join(str(c) for c in cmd)} in {cwd}", "INFO")
    res = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check
    )
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"STDERR: {res.stderr.strip()}", file=sys.stderr)
    return res


def step1_verify_version():
    log("Verifying v1.50 Version Bump in index.html & sw.js...", "STEP")
    
    # 1. Check index.html
    index_path = GHN_DIR / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing {index_path}")
    index_content = index_path.read_text(encoding="utf-8")
    
    if "Version V1.50" not in index_content and "Version v1.50" not in index_content and "v1.50" not in index_content:
        raise ValueError("GHN168/index.html does not contain 'Version V1.50' string!")
    if "app.js?v=150" not in index_content:
        raise ValueError("GHN168/index.html does not contain 'app.js?v=150' cache buster!")
    log("index.html: Verified 'Version V1.50' & 'app.js?v=150'", "SUCCESS")

    # 2. Check sw.js
    sw_path = GHN_DIR / "sw.js"
    if not sw_path.exists():
        raise FileNotFoundError(f"Missing {sw_path}")
    sw_content = sw_path.read_text(encoding="utf-8")
    
    if "ghn168-cache-v150" not in sw_content:
        raise ValueError("GHN168/sw.js does not contain CACHE_NAME 'ghn168-cache-v150'!")
    if "app.js?v=150" not in sw_content:
        raise ValueError("GHN168/sw.js does not contain 'app.js?v=150' in ASSETS list!")
    log("sw.js: Verified CACHE_NAME 'ghn168-cache-v150' & 'app.js?v=150'", "SUCCESS")


def step2_copy_web_files():
    log(f"Syncing Web Files to {CHZ_ROOM_GHN_DIR}...", "STEP")
    CHZ_ROOM_GHN_DIR.mkdir(parents=True, exist_ok=True)

    # Copy files
    for filename in SYNC_FILES:
        src = GHN_DIR / filename
        dst = CHZ_ROOM_GHN_DIR / filename
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        shutil.copy(src, dst)
        log(f"Copied file: {filename} -> ChZ_Room/GHN168/{filename}", "SUCCESS")

    # Copy directories
    for dirname in SYNC_DIRS:
        src_dir = GHN_DIR / dirname
        dst_dir = CHZ_ROOM_GHN_DIR / dirname
        if not src_dir.exists():
            raise FileNotFoundError(f"Source dir not found: {src_dir}")
        shutil.copytree(src_dir, dst_dir, copy_function=shutil.copy, dirs_exist_ok=True)
        log(f"Copied directory: {dirname}/ -> ChZ_Room/GHN168/{dirname}/", "SUCCESS")


def step3_git_deploy():
    log("Performing Git Staging, Commit, and Push to origin main...", "STEP")
    
    # 1. git add
    run_cmd(["git", "add", "GHN168/", "ChZ_Room/GHN168/"], cwd=REPO_ROOT)
    log("Staged GHN168/ and ChZ_Room/GHN168/", "SUCCESS")

    # 2. Check if there are changes to commit
    diff_status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(REPO_ROOT)
    )
    if diff_status.returncode == 0:
        log("No changes staged to commit. Working tree clean.", "WARN")
    else:
        # Commit
        run_cmd(["git", "commit", "-m", COMMIT_MESSAGE], cwd=REPO_ROOT)
        log("Committed changes successfully", "SUCCESS")

    # 3. git push origin main
    push_res = run_cmd(["git", "push", "origin", "main"], cwd=REPO_ROOT)
    log("Pushed to origin main successfully", "SUCCESS")

    # 4. Get latest commit hash
    hash_res = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True
    )
    commit_hash = hash_res.stdout.strip()
    
    log(f"Current HEAD Commit Hash: {commit_hash}", "SUCCESS")
    return commit_hash


def main():
    print("=" * 70)
    print("🚀 GHN168 v1.50 Deployment Pipeline - GitHub & Vercel Trigger")
    print("=" * 70)
    try:
        step1_verify_version()
        step2_copy_web_files()
        commit_hash = step3_git_deploy()
        
        print("\n" + "=" * 70)
        log("DEPLOYMENT COMPLETED SUCCESSFULLY! 🎉", "SUCCESS")
        print(f"📌 Latest Commit Hash: {commit_hash}")
        print(f"📌 Branch: main")
        print(f"📌 Targets: GHN168/ & ChZ_Room/GHN168/")
        print("=" * 70)
    except Exception as e:
        log(f"Deployment failed: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
