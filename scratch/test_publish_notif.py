import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join('/Users/chz/Desktop/ChZ_Agent_Corp/', 'WTJ_Content_Studio', 'Team_Agent_Content', 'skills'))
from notion_helper import NotionHelper

def main():
    helper = NotionHelper()
    print("🔍 Fetching pages with status '5_Approved'...")
    pages = helper.fetch_pages_by_status("5_Approved")
    
    target_page = None
    for p in pages:
        if "กอฟ อินพลู" in p["title"] and "30 sec" in p["title"]:
            target_page = p
            break
            
    if not target_page:
        print("❌ Could not find target page for 'กอฟ อินพลู 30 sec'. Available titles:")
        for p in pages:
            print(f"- {p['title']}")
        return
        
    page_id = target_page["id"]
    original_publish_date = target_page["publish_date"]
    print(f"🎯 Found target page: '{target_page['title']}'")
    print(f"   Original Publish Date: {original_publish_date}")
    
    # 1. Update Publish Date to the past (yesterday)
    past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT12:00:00.000+07:00")
    print(f"🔄 Temporarily setting Publish Date to: {past_date}")
    url = f"https://api.notion.com/v1/pages/{page_id}"
    patch_data = {
        "properties": {
            "Publish Date": {
                "date": {
                    "start": past_date
                }
            }
        }
    }
    res = helper._make_request(url, method="PATCH", data=patch_data)
    if not res:
        print("❌ Failed to update Notion card date to past.")
        return
        
    try:
        # 2. Run facebook_publisher.py in dry-run mode for Reels queue
        print("🚀 Running facebook_publisher.py --from-notes --queue Reels_Under1Min --dry-run...")
        cmd = ["/Users/chz/Desktop/ChZ_Agent_Corp/venv/bin/python3", 
               "/Users/chz/Desktop/ChZ_Agent_Corp/WTJ_Content_Studio/Team_Agent_Content/skills/facebook_publisher.py", 
               "--from-notes", "--queue", "Reels_Under1Min", "--dry-run"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        print("\n--- Command Output ---")
        print(proc.stdout)
        print(proc.stderr)
        print("----------------------\n")
    finally:
        # 3. Restore original Publish Date
        print(f"🔄 Restoring original Publish Date: {original_publish_date}")
        restore_data = {
            "properties": {
                "Publish Date": {
                    "date": {
                        "start": original_publish_date
                    }
                }
            }
        }
        helper._make_request(url, method="PATCH", data=restore_data)
        print("✅ Restored original date!")

if __name__ == "__main__":
    main()
