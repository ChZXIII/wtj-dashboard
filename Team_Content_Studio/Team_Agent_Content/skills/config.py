#!/usr/bin/env python3
import os

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

# Dashboard Paths
LOCAL_DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "Personal_Assistance_HQ", "Personal_Assistance_Team", "M", "html")
GITHUB_DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "dashboard")
SIDEKICK_PROJECT_DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "AI_Sidekick_Project", "dashboard")

# Video Search Directories
VIDEO_SEARCH_DIRS = [
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "raw_vdo_short", "processed"),
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "raw_vdo_3-5min", "processed"),
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "raw_vdo_short"),
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "raw_vdo_3-5min"),
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials", "raw_vdo_full"),
    os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "WTJ_Project", "WTJ_Story", "workspace", "1_raw_materials"),
]

def print_paths():
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"LOCAL_DASHBOARD_DIR: {LOCAL_DASHBOARD_DIR}")
    print(f"GITHUB_DASHBOARD_DIR: {GITHUB_DASHBOARD_DIR}")
    print(f"SIDEKICK_PROJECT_DASHBOARD_DIR: {SIDEKICK_PROJECT_DASHBOARD_DIR}")

if __name__ == "__main__":
    print_paths()
