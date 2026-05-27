#!/usr/bin/env python3
import os
import sys

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
# Add WTJ_Content_Studio/Team_Agent_Content/skills to sys.path
skills_dir = os.path.join(PROJECT_ROOT, "WTJ_Content_Studio", "Team_Agent_Content", "skills")
if skills_dir not in sys.path:
    sys.path.append(skills_dir)

from notion_helper import NotionHelper

def main():
    notion = NotionHelper()
    
    # We query the database to get all cards
    url = f"https://api.notion.com/v1/databases/{notion.database_id}/query"
    title_prop_name = notion.get_title_property_name()
    
    print("🔍 Searching for [THU_Text] and [SUN_Text] cards in Notion...")
    
    has_more = True
    start_cursor = None
    target_pages = []
    
    while has_more:
        data = {}
        if start_cursor:
            data["start_cursor"] = start_cursor
        
        # Query pages in status 4_Review to target them
        data["filter"] = {
            "property": "Status",
            "select": {
                "equals": "4_Review"
            }
        }
        
        res = notion._make_request(url, method="POST", data=data)
        if res and "results" in res:
            for page in res["results"]:
                properties = page.get("properties", {})
                name_prop = properties.get(title_prop_name, {})
                if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
                    title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
                    if title.startswith("[THU_Text]") or title.startswith("[SUN_Text]"):
                        target_pages.append((page["id"], title))
            
            has_more = res.get("has_more", False)
            start_cursor = res.get("next_cursor")
        else:
            has_more = False
            
    print(f"📌 Found {len(target_pages)} guest cards to clear.")
    
    for page_id, title in target_pages:
        print(f"🗑️ Archiving card: '{title}'...")
        # Patch archived = True
        patch_url = f"https://api.notion.com/v1/pages/{page_id}"
        notion._make_request(patch_url, method="PATCH", data={"archived": True})
        
    print("🎉 All guest cards have been cleared from Notion!")

if __name__ == "__main__":
    main()
