import sys
import os

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'WTJ_Content_Studio', 'Team_Agent_Content', 'skills'))

from notion_helper import NotionHelper

def main():
    helper = NotionHelper()
    
    # Fetch pages in '4_Review' status
    print("🔍 Fetching pages in '4_Review' status...")
    pages = helper.fetch_pages_by_status("4_Review")
    
    updated_count = 0
    for p in pages:
        platforms = p['platforms']
        if "Reels" in platforms:
            print(f"\nFound Reels card: '{p['title']}'")
            new_platforms = list(set(platforms + ["YouTube", "TikTok"]))
            print(f"Current platforms: {platforms} -> New platforms: {new_platforms}")
            
            # Perform update
            page_id = p['id']
            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {
                "properties": {
                    "Platform": {
                        "multi_select": [{"name": plat} for plat in new_platforms]
                    }
                }
            }
            res = helper._make_request(url, method="PATCH", data=data)
            if res:
                print(f"✅ Successfully updated platform tags for '{p['title']}'")
                updated_count += 1
            else:
                print(f"❌ Failed to update '{p['title']}'")
                
    print(f"\n🎉 Done! Updated {updated_count} Reels cards in Notion.")

if __name__ == "__main__":
    main()
