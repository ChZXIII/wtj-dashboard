import sys
import os

sys.path.append(os.path.join('/Users/chz/Desktop/ChZ_Agent_Corp/', 'Team_Content_Studio', 'Team_Agent_Content', 'skills'))
from notion_helper import NotionHelper

helper = NotionHelper()
page_id = "36b1b328-5b0e-8154-bb80-e1200e4c7f10"
url = f"https://api.notion.com/v1/pages/{page_id}"

data = {
    "properties": {
        "Publish Date": {
            "date": None
        },
        "Platform": {
            "multi_select": [
                {"name": "Reels"},
                {"name": "YouTube"},
                {"name": "TikTok"}
            ]
        },
        "Status": {
            "select": {
                "name": "4_Review"
            }
        }
    }
}

res = helper._make_request(url, method="PATCH", data=data)
if res:
    print("✅ Successfully restored card to normal!")
else:
    print("❌ Failed to restore card.")
