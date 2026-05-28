import sys
import os
import subprocess
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Team_Content_Studio.Team_Agent_Content.skills.notion_helper import NotionHelper

page_id = "36b1b328-5b0e-8154-bb80-e1200e4c7f10" # Page [8]
helper = NotionHelper()

print("1. Writing temporary token_tiktok.json with mock token...")
token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token_tiktok.json")
mock_token = {
    "access_token": "mock_access_token_value",
    "expires_at": 9999999999, # Far future
    "refresh_token": "mock_refresh_token_value",
    "refresh_expires_at": 9999999999
}
with open(token_path, "w", encoding="utf-8") as f:
    json.dump(mock_token, f)

print("2. Updating Notion page status to '5_Approved' and setting publish date to past...")
# Update Status to 5_Approved
helper.update_page_status(page_id, "5_Approved")

# Set Publish Date to today
url = f"https://api.notion.com/v1/pages/{page_id}"
data = {
    "properties": {
        "Publish Date": {
            "date": {
                "start": "2026-05-25"
            }
        }
    }
}
helper._make_request(url, method="PATCH", data=data)
print("✅ Notion page updated successfully.")

try:
    print("\n3. Running tiktok_publisher.py in Dry-Run mode with mocked env...")
    
    # Run subprocess passing mocked env variables
    env = os.environ.copy()
    env["TIKTOK_CLIENT_KEY"] = "mock_client_key_123"
    env["TIKTOK_CLIENT_SECRET"] = "mock_client_secret_abc"
    
    cmd = ["venv/bin/python3", "Team_Content_Studio/Team_Agent_Content/skills/tiktok_publisher.py", "--dry-run", "--from-notes"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    print("\n--- Command Output ---")
    print(result.stdout)
    print("----------------------")
    if result.stderr:
        print("\n--- Command Stderr ---")
        print(result.stderr)
        print("----------------------")

finally:
    print("\n4. Resetting Notion page status back to '4_Review' and publish date to None...")
    helper.update_page_status(page_id, "4_Review")
    
    # Clear Publish Date
    data_clear = {
        "properties": {
            "Publish Date": {
                "date": None
            }
        }
    }
    helper._make_request(url, method="PATCH", data=data_clear)
    print("✅ Notion page reset successfully.")
    
    # Delete mock token file
    if os.path.exists(token_path):
        os.remove(token_path)
        print("🗑️ Temporary token_tiktok.json deleted.")
