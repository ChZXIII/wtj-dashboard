import os
import plistlib
import subprocess

PROJECT_ROOT = "/Users/chz/Desktop/ChZ_Agent_Corp"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PYTHON3_PATH = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
MASTER_SCRIPT = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills", "wtj_auto_poster.py")
CONTENT_DIR = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "WTJ_Story_Project")

label = "com.wtj.master.temp_test"
plist_path = os.path.join(LAUNCH_AGENTS_DIR, f"{label}.plist")
log_base = os.path.join(CONTENT_DIR, "workspace", "master_temp_test")

# StartCalendarInterval for today at 12:00 PM
plist_data = {
    "Label": label,
    "ProgramArguments": [PYTHON3_PATH, MASTER_SCRIPT, "-q", "Reels_Under1Min"],
    "WorkingDirectory": PROJECT_ROOT,
    "EnvironmentVariables": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    },
    "StartCalendarInterval": {
        "Weekday": 2, # Tuesday
        "Hour": 12,
        "Minute": 0
    },
    "RunAtLoad": False,
    "StandardOutPath": f"{log_base}.out",
    "StandardErrorPath": f"{log_base}.err",
}

# Ensure directory exists
os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)

with open(plist_path, "wb") as f:
    plistlib.dump(plist_data, f)

# Unload old if exists
subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
# Load new
res = subprocess.run(["launchctl", "load", plist_path], capture_output=True)
if res.returncode == 0:
    print("✅ Temporary LaunchAgent com.wtj.master.temp_test registered successfully for Tuesday at 12:00 PM!")
else:
    print(f"❌ Failed to load LaunchAgent: {res.stderr.decode('utf-8')}")
