import sys
import os

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'WTJ_Content_Studio', 'Team_Agent_Content', 'skills'))

from notion_helper import NotionHelper

def main():
    helper = NotionHelper()
    pages = helper.fetch_pages_by_status("4_Review")
    print(f"FOUND {len(pages)} PAGES IN 4_Review\n")
    for idx, p in enumerate(pages, 1):
        print(f"--- CARD {idx} ---")
        print(f"TITLE: {p['title']}")
        print(f"PLATFORMS: {p['platforms']}")
        print(f"PUBLISH DATE: {p['publish_date']}")
        print("CONTENT:")
        content = helper.get_page_content_text(p['id'])
        print(content)
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
