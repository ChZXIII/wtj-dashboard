import sys
import os

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'Team_Content_Studio', 'Team_Agent_Content', 'skills'))

from notion_helper import NotionHelper

def main():
    helper = NotionHelper()
    
    print("🔍 Fetching pages in '4_Review' status...")
    pages = helper.fetch_pages_by_status("4_Review")
    
    cleared_count = 0
    for p in pages:
        page_id = p['id']
        print(f"🧹 Clearing Publish Date for: '{p['title']}'")
        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = {
            "properties": {
                "Publish Date": {
                    "date": None
                }
            }
        }
        res = helper._make_request(url, method="PATCH", data=data)
        if res:
            cleared_count += 1
            
    print(f"\n🎉 Done! Cleared Publish Date for {cleared_count} pages in Notion.")

if __name__ == "__main__":
    main()
